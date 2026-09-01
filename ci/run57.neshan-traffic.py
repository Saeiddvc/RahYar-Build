from pathlib import Path

root = Path(".")

traffic = root / "app/src/main/java/ir/rahyar/app/data/remote/TrafficApi.kt"
t = traffic.read_text()
start = t.index("class HereTrafficApi(")
end = t.index("class UnavailableTrafficApi", start)
neshan = r'''class NeshanTrafficApi(
    private val http: OkHttpClient,
    private val apiKey: String
) : TrafficApi {
    override suspend fun getTraffic(polyline: List<LatLng>): TrafficInfo = withContext(Dispatchers.IO) {
        if (polyline.size < 2 || apiKey.isBlank()) {
            return@withContext TrafficInfo(emptyList(), isLive = false)
        }

        val constrained = routeConstraintPoints(polyline)
        val liveSeconds = requestDurationSeconds("https://api.neshan.org/v4/direction", constrained)
        val baselineSeconds = requestDurationSeconds("https://api.neshan.org/v4/direction/no-traffic", constrained)
        val jamFactor = neshanJamFactor(liveSeconds, baselineSeconds)
            ?: return@withContext TrafficInfo(emptyList(), isLive = false)
        val segment = TrafficSegment(
            start = polyline.first(),
            end = polyline.last(),
            level = neshanTrafficLevel(jamFactor),
            jamFactor = jamFactor
        )
        TrafficInfo(segments = listOf(segment), isLive = true)
    }

    private fun requestDurationSeconds(endpoint: String, points: List<LatLng>): Double {
        val url = endpoint.toHttpUrl().newBuilder()
            .addQueryParameter("type", "car")
            .addQueryParameter("origin", "${points.first().latitude},${points.first().longitude}")
            .addQueryParameter("destination", "${points.last().latitude},${points.last().longitude}")
            .addQueryParameter("avoidTrafficZone", "false")
            .addQueryParameter("avoidOddEvenZone", "false")
            .addQueryParameter("alternative", "false")
            .apply {
                val middle = points.drop(1).dropLast(1)
                if (middle.isNotEmpty()) {
                    addQueryParameter("waypoints", middle.joinToString("|") { "${it.latitude},${it.longitude}" })
                }
            }
            .build()
        val request = Request.Builder().url(url).addHeader("Api-Key", apiKey).get().build()
        http.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                if (response.code in setOf(481, 482)) {
                    ProviderTelemetry.recordFailure(
                        ProviderTelemetry.NESHAN_TRAFFIC,
                        null,
                        "Neshan Traffic quota exhausted",
                        rateLimited = true
                    )
                }
                throw IOException("Neshan Traffic HTTP ${response.code}")
            }
            return parseNeshanDurationSeconds(JSONObject(response.body?.string().orEmpty()))
                ?: throw IOException("Neshan Traffic response has no valid route duration")
        }
    }
}

internal fun routeConstraintPoints(polyline: List<LatLng>, maxPoints: Int = 6): List<LatLng> {
    if (polyline.size <= maxPoints) return polyline
    return (0 until maxPoints).map { sample ->
        polyline[((polyline.lastIndex.toDouble() * sample) / (maxPoints - 1)).toInt()]
    }.distinct()
}

internal fun parseNeshanDurationSeconds(json: JSONObject): Double? {
    val route = json.optJSONArray("routes")?.optJSONObject(0) ?: return null
    val legs = route.optJSONArray("legs") ?: return null
    var total = 0.0
    for (i in 0 until legs.length()) {
        val value = legs.optJSONObject(i)?.optJSONObject("duration")?.optDouble("value", Double.NaN)
            ?: return null
        if (!value.isFinite() || value < 0.0) return null
        total += value
    }
    return total.takeIf { it > 0.0 }
}

internal fun neshanJamFactor(liveSeconds: Double, baselineSeconds: Double): Double? {
    if (!liveSeconds.isFinite() || !baselineSeconds.isFinite() || liveSeconds <= 0.0 || baselineSeconds <= 0.0) return null
    return (((liveSeconds - baselineSeconds).coerceAtLeast(0.0) / baselineSeconds) * 10.0)
        .coerceIn(0.0, 10.0)
}

internal fun neshanTrafficLevel(jamFactor: Double): TrafficLevel = when {
    jamFactor < 2.0 -> TrafficLevel.LIGHT
    jamFactor < 5.0 -> TrafficLevel.MEDIUM
    else -> TrafficLevel.HEAVY
}

'''
t = t[:start] + neshan + t[end:]
traffic.write_text(t)

health = root / "app/src/main/java/ir/rahyar/app/core/provider/ProviderHealth.kt"
h = health.read_text().replace('const val HERE_TRAFFIC = "here_traffic"', 'const val NESHAN_TRAFFIC = "neshan_traffic"')
health.write_text(h)

app = root / "app/src/main/java/ir/rahyar/app/di/AppModule.kt"
a = app.read_text()
a = a.replace("BuildConfig.HERE_API_KEY", "BuildConfig.NESHAN_API_KEY")
a = a.replace("ProviderTelemetry.HERE_TRAFFIC", "ProviderTelemetry.NESHAN_TRAFFIC")
a = a.replace("HereTrafficApi(http, it)", "NeshanTrafficApi(http, it)")
a = a.replace("import ir.rahyar.app.data.remote.HereTrafficApi", "import ir.rahyar.app.data.remote.NeshanTrafficApi")
app.write_text(a)

gradle = root / "app/build.gradle.kts"
g = gradle.read_text()
g = g.replace('val hereApiKey = System.getenv("HERE_API_KEY") ?: ""', 'val neshanApiKey = System.getenv("NESHAN_API_KEY") ?: ""')
g = g.replace('buildConfigField("String", "HERE_API_KEY", "\\"${hereApiKey.escapeBuildConfig()}\\"")', 'buildConfigField("String", "NESHAN_API_KEY", "\\"${neshanApiKey.escapeBuildConfig()}\\"")')
gradle.write_text(g)

provider_test = root / "app/src/test/java/ir/rahyar/app/core/provider/ProviderTelemetryTest.kt"
p = provider_test.read_text().replace("ProviderTelemetry.HERE_TRAFFIC", "ProviderTelemetry.NESHAN_TRAFFIC")
provider_test.write_text(p)

neshan_test = root / "app/src/test/java/ir/rahyar/app/data/remote/NeshanTrafficApiTest.kt"
neshan_test.write_text(r'''package ir.rahyar.app.data.remote

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.TrafficLevel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class NeshanTrafficApiTest {
    @Test fun liveDelayProducesHeavyTrafficFromRealDurationRatio() {
        val jamFactor = neshanJamFactor(liveSeconds = 900.0, baselineSeconds = 600.0)
        assertEquals(5.0, jamFactor ?: -1.0, 0.001)
        assertEquals(TrafficLevel.HEAVY, neshanTrafficLevel(jamFactor ?: -1.0))
    }

    @Test fun invalidBaselineCannotProduceLiveTraffic() {
        assertNull(neshanJamFactor(liveSeconds = 900.0, baselineSeconds = 0.0))
    }

    @Test fun longRouteIsConstrainedWithEndpointsPreserved() {
        val route = (0..20).map { LatLng(35.0 + it / 100.0, 51.0 + it / 100.0) }
        val points = routeConstraintPoints(route)
        assertEquals(6, points.size)
        assertEquals(route.first(), points.first())
        assertEquals(route.last(), points.last())
    }
}
''')
