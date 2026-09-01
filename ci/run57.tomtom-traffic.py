from pathlib import Path

root = Path(".")

traffic = root / "app/src/main/java/ir/rahyar/app/data/remote/TrafficApi.kt"
t = traffic.read_text()
start = t.index("class HereTrafficApi(")
end = t.index("class UnavailableTrafficApi", start)
tomtom = r'''class TomTomTrafficApi(
    private val http: OkHttpClient,
    private val apiKey: String
) : TrafficApi {

    override suspend fun getTraffic(polyline: List<LatLng>): TrafficInfo = withContext(Dispatchers.IO) {
        if (polyline.size < 2 || apiKey.isBlank()) {
            return@withContext TrafficInfo(emptyList(), isLive = false)
        }

        val sampleCount = minOf(6, polyline.size)
        val indices = (0 until sampleCount).map { sample ->
            ((polyline.lastIndex.toDouble() * sample) / (sampleCount - 1)).toInt()
        }.distinct()

        val segments = indices.mapNotNull { index ->
            val point = polyline[index]
            val url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
                .toHttpUrl().newBuilder()
                .addQueryParameter("point", "${point.latitude},${point.longitude}")
                .addQueryParameter("unit", "KMPH")
                .addQueryParameter("openLr", "false")
                .addQueryParameter("key", apiKey)
                .build()
            val request = Request.Builder().url(url).get().build()
            http.newCall(request).execute().use { response ->
                ProviderTelemetry.recordQuota(
                    ProviderTelemetry.TOMTOM_TRAFFIC,
                    response.header("X-RateLimit-Remaining")?.toIntOrNull()
                )
                if (!response.isSuccessful) {
                    if (response.code == 429) {
                        ProviderTelemetry.recordFailure(
                            ProviderTelemetry.TOMTOM_TRAFFIC,
                            null,
                            "TomTom Traffic quota exhausted",
                            rateLimited = true
                        )
                    }
                    throw IOException("TomTom Traffic HTTP ${response.code}")
                }
                parseTomTomFlowSegment(JSONObject(response.body?.string().orEmpty()))
            }
        }.distinctBy { listOf(it.start.latitude, it.start.longitude, it.end.latitude, it.end.longitude) }

        TrafficInfo(segments = segments, isLive = segments.isNotEmpty())
    }
}

internal fun parseTomTomFlowSegment(json: JSONObject): TrafficSegment? {
    val flow = json.optJSONObject("flowSegmentData") ?: return null
    if (!flow.has("currentSpeed") || !flow.has("freeFlowSpeed")) return null
    val currentSpeed = flow.optDouble("currentSpeed", Double.NaN)
    val freeFlowSpeed = flow.optDouble("freeFlowSpeed", Double.NaN)
    if (!currentSpeed.isFinite() || !freeFlowSpeed.isFinite() || freeFlowSpeed <= 0.0) return null
    val coordinates = flow.optJSONObject("coordinates")?.optJSONArray("coordinate") ?: return null
    val points = buildList {
        for (i in 0 until coordinates.length()) {
            val point = coordinates.optJSONObject(i) ?: continue
            if (point.has("latitude") && point.has("longitude")) {
                add(LatLng(point.getDouble("latitude"), point.getDouble("longitude")))
            }
        }
    }
    if (points.size < 2) return null
    val jamFactor = (((freeFlowSpeed - currentSpeed).coerceAtLeast(0.0) / freeFlowSpeed) * 10.0)
        .coerceIn(0.0, 10.0)
    val level = when {
        jamFactor < 4.0 -> TrafficLevel.LIGHT
        jamFactor < 7.0 -> TrafficLevel.MEDIUM
        else -> TrafficLevel.HEAVY
    }
    return TrafficSegment(points.first(), points.last(), level, jamFactor)
}

'''
t = t[:start] + tomtom + t[end:]
traffic.write_text(t)

health = root / "app/src/main/java/ir/rahyar/app/core/provider/ProviderHealth.kt"
h = health.read_text().replace('const val HERE_TRAFFIC = "here_traffic"', 'const val TOMTOM_TRAFFIC = "tomtom_traffic"')
health.write_text(h)

app = root / "app/src/main/java/ir/rahyar/app/di/AppModule.kt"
a = app.read_text()
a = a.replace("BuildConfig.HERE_API_KEY", "BuildConfig.TOMTOM_TRAFFIC_API_KEY")
a = a.replace("ProviderTelemetry.HERE_TRAFFIC", "ProviderTelemetry.TOMTOM_TRAFFIC")
a = a.replace("HereTrafficApi(http, it)", "TomTomTrafficApi(http, it)")
a = a.replace("import ir.rahyar.app.data.remote.HereTrafficApi", "import ir.rahyar.app.data.remote.TomTomTrafficApi")
app.write_text(a)

gradle = root / "app/build.gradle.kts"
g = gradle.read_text()
g = g.replace('val hereApiKey = System.getenv("HERE_API_KEY") ?: ""', 'val tomTomTrafficApiKey = System.getenv("TOMTOM_TRAFFIC_API_KEY") ?: ""')
g = g.replace('buildConfigField("String", "HERE_API_KEY", "\\"${hereApiKey.escapeBuildConfig()}\\"")', 'buildConfigField("String", "TOMTOM_TRAFFIC_API_KEY", "\\"${tomTomTrafficApiKey.escapeBuildConfig()}\\"")')
gradle.write_text(g)

provider_test = root / "app/src/test/java/ir/rahyar/app/core/provider/ProviderTelemetryTest.kt"
p = provider_test.read_text().replace("ProviderTelemetry.HERE_TRAFFIC", "ProviderTelemetry.TOMTOM_TRAFFIC")
provider_test.write_text(p)

tomtom_test = root / "app/src/test/java/ir/rahyar/app/data/remote/TomTomTrafficApiTest.kt"
tomtom_test.write_text(r'''package ir.rahyar.app.data.remote

import ir.rahyar.app.domain.models.TrafficLevel
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class TomTomTrafficApiTest {
    @Test fun validLiveFlowBecomesRealTrafficSegment() {
        val segment = parseTomTomFlowSegment(JSONObject("""{
          "flowSegmentData": {
            "currentSpeed": 20,
            "freeFlowSpeed": 80,
            "coordinates": {"coordinate": [
              {"latitude":35.7219,"longitude":51.3347},
              {"latitude":35.7224,"longitude":51.3361}
            ]}
          }
        }"""))
        assertNotNull(segment)
        assertEquals(TrafficLevel.HEAVY, segment?.level)
        assertEquals(7.5, segment?.jamFactor ?: -1.0, 0.001)
    }

    @Test fun missingSpeedCannotBePresentedAsLiveTraffic() {
        assertNull(parseTomTomFlowSegment(JSONObject("""{
          "flowSegmentData": {"coordinates":{"coordinate":[]}}
        }""")))
    }
}
''')
