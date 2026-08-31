from pathlib import Path

root = Path(".")

weather_model = root / "app/src/main/java/ir/rahyar/app/domain/models/Weather.kt"
weather_model.write_text("""package ir.rahyar.app.domain.models

enum class WeatherHazard {
    RAIN,
    SNOW,
    FOG,
    THUNDERSTORM,
    STRONG_WIND
}

data class RouteWeatherSnapshot(
    val location: LatLng,
    val temperatureC: Int,
    val weatherCode: Int,
    val precipitationMm: Double,
    val windSpeedKmh: Double,
    val hazards: Set<WeatherHazard>
)

data class WeatherInfo(
    val summary: String,
    val alerts: List<String>,
    val isLive: Boolean = false,
    val timeline: List<RouteWeatherSnapshot> = emptyList()
)
""")

hazards = root / "app/src/main/java/ir/rahyar/app/core/weather/WeatherHazards.kt"
hazards.parent.mkdir(parents=True, exist_ok=True)
hazards.write_text("""package ir.rahyar.app.core.weather

import ir.rahyar.app.domain.models.RouteWeatherSnapshot
import ir.rahyar.app.domain.models.WeatherHazard
import ir.rahyar.app.domain.models.WeatherInfo

fun classifyWeatherHazards(
    weatherCode: Int,
    precipitationMm: Double,
    windSpeedKmh: Double
): Set<WeatherHazard> = buildSet {
    if (weatherCode in setOf(45, 48)) add(WeatherHazard.FOG)
    if (weatherCode in setOf(71, 73, 75, 77, 85, 86)) add(WeatherHazard.SNOW)
    if (weatherCode in setOf(95, 96, 99)) add(WeatherHazard.THUNDERSTORM)
    if (
        weatherCode in setOf(51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82) ||
        precipitationMm > 0.5
    ) add(WeatherHazard.RAIN)
    if (windSpeedKmh >= 45.0) add(WeatherHazard.STRONG_WIND)
}

fun buildWeatherInfoFromSnapshots(
    snapshots: List<RouteWeatherSnapshot>
): WeatherInfo {
    if (snapshots.isEmpty()) {
        return WeatherInfo(
            summary = "اطلاعات آب‌وهوا در دسترس نیست",
            alerts = emptyList(),
            isLive = false,
            timeline = emptyList()
        )
    }

    val conditions = snapshots.map { weatherLabel(it.weatherCode) }.distinct()
    val minTemp = snapshots.minOf { it.temperatureC }
    val maxTemp = snapshots.maxOf { it.temperatureC }
    val hazards = snapshots.flatMap { it.hazards }.toSet()

    val alerts = buildList {
        if (WeatherHazard.FOG in hazards) add("مه در بخشی از مسیر؛ دید را کاهش دهید")
        if (WeatherHazard.SNOW in hazards) add("برف در بخشی از مسیر؛ سرعت و فاصله طولی را کاهش دهید")
        if (WeatherHazard.RAIN in hazards) add("بارش در بخشی از مسیر؛ سطح جاده ممکن است لغزنده باشد")
        if (WeatherHazard.THUNDERSTORM in hazards) add("رعدوبرق در بخشی از مسیر")
        if (WeatherHazard.STRONG_WIND in hazards) add("وزش باد شدید در بخشی از مسیر")
    }

    val summary = buildString {
        append(conditions.joinToString("، "))
        append(" • ")
        if (minTemp == maxTemp) append("${minTemp}°") else append("${minTemp} تا ${maxTemp}°")
    }

    return WeatherInfo(
        summary = summary,
        alerts = alerts,
        isLive = true,
        timeline = snapshots
    )
}

private fun weatherLabel(code: Int): String = when (code) {
    0 -> "صاف"
    1, 2, 3 -> "نیمه‌ابری"
    45, 48 -> "مه‌آلود"
    51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82 -> "بارانی"
    71, 73, 75, 77, 85, 86 -> "برفی"
    95, 96, 99 -> "رعدوبرق"
    else -> "وضعیت متغیر"
}
""")

weather_api = root / "app/src/main/java/ir/rahyar/app/data/remote/WeatherApi.kt"
weather_api.write_text("""package ir.rahyar.app.data.remote

import ir.rahyar.app.core.weather.buildWeatherInfoFromSnapshots
import ir.rahyar.app.core.weather.classifyWeatherHazards
import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.RouteWeatherSnapshot
import ir.rahyar.app.domain.models.WeatherInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.IOException
import kotlin.math.roundToInt

interface WeatherApi {
    suspend fun getWeatherAlong(polyline: List<LatLng>): WeatherInfo
}

class OpenMeteoWeatherApi(
    private val http: OkHttpClient
) : WeatherApi {

    override suspend fun getWeatherAlong(polyline: List<LatLng>): WeatherInfo {
        if (polyline.isEmpty()) {
            return WeatherInfo("اطلاعات آب‌وهوا در دسترس نیست", emptyList(), false)
        }

        val sampled = sample(polyline, 5)
        val snapshots = coroutineScope {
            sampled.map { point ->
                async {
                    runCatching { fetch(point) }.getOrNull()
                }
            }.awaitAll().filterNotNull()
        }

        return buildWeatherInfoFromSnapshots(snapshots)
    }

    private suspend fun fetch(point: LatLng): RouteWeatherSnapshot = withContext(Dispatchers.IO) {
        val url = "https://api.open-meteo.com/v1/forecast".toHttpUrl().newBuilder()
            .addQueryParameter("latitude", point.latitude.toString())
            .addQueryParameter("longitude", point.longitude.toString())
            .addQueryParameter("current", "temperature_2m,weather_code,precipitation,wind_speed_10m")
            .addQueryParameter("timezone", "auto")
            .build()

        val request = Request.Builder()
            .url(url)
            .header("User-Agent", "RahYar/1.6.1 Android")
            .get()
            .build()

        http.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("Open-Meteo HTTP ${response.code}")
            val current = JSONObject(response.body?.string().orEmpty()).getJSONObject("current")
            val code = current.optInt("weather_code", -1)
            val precipitation = current.optDouble("precipitation", 0.0)
            val wind = current.optDouble("wind_speed_10m", 0.0)
            RouteWeatherSnapshot(
                location = point,
                temperatureC = current.optDouble("temperature_2m", 0.0).roundToInt(),
                weatherCode = code,
                precipitationMm = precipitation,
                windSpeedKmh = wind,
                hazards = classifyWeatherHazards(code, precipitation, wind)
            )
        }
    }

    private fun sample(points: List<LatLng>, maxPoints: Int): List<LatLng> {
        if (points.size <= maxPoints) return points
        if (maxPoints <= 1) return listOf(points[points.size / 2])
        val last = points.lastIndex
        return (0 until maxPoints)
            .map { i -> points[((last.toDouble() * i) / (maxPoints - 1)).roundToInt()] }
            .distinct()
    }
}
""")

test = root / "app/src/test/java/ir/rahyar/app/core/weather/WeatherHazardsTest.kt"
test.parent.mkdir(parents=True, exist_ok=True)
test.write_text("""package ir.rahyar.app.core.weather

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.RouteWeatherSnapshot
import ir.rahyar.app.domain.models.WeatherHazard
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class WeatherHazardsTest {
    @Test fun rainIsDetectedFromWeatherCode() {
        assertTrue(WeatherHazard.RAIN in classifyWeatherHazards(61, 0.0, 10.0))
    }

    @Test fun rainIsDetectedFromMeasuredPrecipitation() {
        assertTrue(WeatherHazard.RAIN in classifyWeatherHazards(3, 0.8, 10.0))
    }

    @Test fun snowIsDetected() {
        assertTrue(WeatherHazard.SNOW in classifyWeatherHazards(75, 0.0, 10.0))
    }

    @Test fun fogIsDetected() {
        assertTrue(WeatherHazard.FOG in classifyWeatherHazards(45, 0.0, 5.0))
    }

    @Test fun clearWeatherDoesNotCreateFalseHazard() {
        assertTrue(classifyWeatherHazards(0, 0.0, 8.0).isEmpty())
    }

    @Test fun timelinePreservesLiveRouteSnapshots() {
        val items = listOf(
            RouteWeatherSnapshot(
                location = LatLng(35.83, 50.95),
                temperatureC = 20,
                weatherCode = 0,
                precipitationMm = 0.0,
                windSpeedKmh = 8.0,
                hazards = emptySet()
            ),
            RouteWeatherSnapshot(
                location = LatLng(35.82, 51.00),
                temperatureC = 18,
                weatherCode = 61,
                precipitationMm = 1.2,
                windSpeedKmh = 12.0,
                hazards = setOf(WeatherHazard.RAIN)
            )
        )
        val info = buildWeatherInfoFromSnapshots(items)
        assertTrue(info.isLive)
        assertEquals(2, info.timeline.size)
        assertFalse(info.alerts.isEmpty())
        assertTrue(info.alerts.any { "بارش" in it })
    }
}
""")

nav_host = root / "app/src/main/java/ir/rahyar/app/navigation/RahyarNavHost.kt"
nh = nav_host.read_text()
target = """                destinationSearchRepository = destinationSearchRepository,
                roadAwarenessRepository = roadAwarenessRepository,
                navigationSession = navigationSession"""
replacement = """                destinationSearchRepository = destinationSearchRepository,
                roadAwarenessRepository = roadAwarenessRepository,
                weatherRepository = weatherRepository,
                navigationSession = navigationSession"""
if target not in nh:
    raise SystemExit("Run45 RahyarNavHost ActiveNavigationScreen target not found")
nav_host.write_text(nh.replace(target, replacement, 1))

active = root / "app/src/main/java/ir/rahyar/app/ui/screens/ActiveNavigationScreen.kt"
a = active.read_text()

if "import ir.rahyar.app.domain.models.WeatherInfo" not in a:
    a = a.replace(
        "import ir.rahyar.app.domain.models.RouteType\n",
        "import ir.rahyar.app.domain.models.RouteType\nimport ir.rahyar.app.domain.models.WeatherInfo\n",
        1
    )
if "import ir.rahyar.app.domain.repository.WeatherRepository" not in a:
    a = a.replace(
        "import ir.rahyar.app.domain.repository.SettingsRepository\n",
        "import ir.rahyar.app.domain.repository.SettingsRepository\nimport ir.rahyar.app.domain.repository.WeatherRepository\n",
        1
    )
if "import kotlinx.coroutines.delay" not in a:
    a = a.replace(
        "import kotlinx.coroutines.launch\n",
        "import kotlinx.coroutines.delay\nimport kotlinx.coroutines.launch\n",
        1
    )

signature = """    destinationSearchRepository: DestinationSearchRepository,
    roadAwarenessRepository: RoadAwarenessRepository,
    navigationSession: NavigationSession"""
if a.count(signature) < 2:
    raise SystemExit(f"Run45 expected two ActiveNavigation signatures, found {a.count(signature)}")
a = a.replace(
    signature,
    """    destinationSearchRepository: DestinationSearchRepository,
    roadAwarenessRepository: RoadAwarenessRepository,
    weatherRepository: WeatherRepository,
    navigationSession: NavigationSession"""
)

call = """        destinationSearchRepository = destinationSearchRepository,
        roadAwarenessRepository = roadAwarenessRepository,
        navigationSession = navigationSession,"""
if call not in a:
    raise SystemExit("Run45 NavigationHUDScreen call target not found")
a = a.replace(
    call,
    """        destinationSearchRepository = destinationSearchRepository,
        roadAwarenessRepository = roadAwarenessRepository,
        weatherRepository = weatherRepository,
        navigationSession = navigationSession,""",
    1
)

state_anchor = """    var lastSpokenInstruction by remember { mutableStateOf<String?>(null) }
    var lastSpokenDriverAlert by remember { mutableStateOf<String?>(null) }"""
if state_anchor not in a:
    raise SystemExit("Run45 weather state anchor not found")
a = a.replace(
    state_anchor,
    state_anchor + """
    var liveWeather by remember { mutableStateOf<WeatherInfo?>(null) }
    var lastSpokenWeatherAlert by remember { mutableStateOf<String?>(null) }""",
    1
)

effect_anchor = """    LaunchedEffect(active?.currentLocation, active?.speedKmh) {"""
if effect_anchor not in a:
    raise SystemExit("Run45 weather effect anchor not found")
weather_effects = """    LaunchedEffect(active?.route?.id) {
        if (active == null) {
            liveWeather = null
            return@LaunchedEffect
        }
        while (true) {
            val currentRoute = (engine.hudState.value as? NavigationHudState.Active)?.route ?: initialRoute
            liveWeather = runCatching { weatherRepository.getWeatherAlongRoute(currentRoute) }
                .getOrNull()
                ?.takeIf { it.isLive }
            delay(300_000L)
        }
    }

    LaunchedEffect(
        liveWeather?.alerts?.firstOrNull(),
        session.quickSettings.voiceAlertsEnabled,
        voiceEnabled,
        voiceAvailable
    ) {
        val alert = liveWeather?.alerts?.firstOrNull() ?: return@LaunchedEffect
        if (!voiceEnabled || !voiceAvailable || !session.quickSettings.voiceAlertsEnabled) return@LaunchedEffect
        if (alert == lastSpokenWeatherAlert) return@LaunchedEffect
        lastSpokenWeatherAlert = alert
        voiceManager.speak(alert, utteranceId = "rahyar-weather-alert")
    }

"""
a = a.replace(effect_anchor, weather_effects + effect_anchor, 1)

hud_anchor = """        if (active != null) {
            NavigationHud(hud)
        } else {"""
if hud_anchor not in a:
    raise SystemExit("Run45 HUD weather reaction anchor not found")
hud_reaction = """        if (active != null) {
            NavigationHud(hud)
            liveWeather?.takeIf { it.isLive }?.let { weather ->
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    tonalElevation = 2.dp
                ) {
                    Column(Modifier.padding(horizontal = 14.dp, vertical = 6.dp)) {
                        Text(
                            text = "آب‌وهوا: ${weather.summary}",
                            style = MaterialTheme.typography.bodySmall
                        )
                        weather.alerts.firstOrNull()?.let { alert ->
                            Text(
                                text = "هشدار مسیر: $alert",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.error
                            )
                        }
                    }
                }
            }
        } else {"""
a = a.replace(hud_anchor, hud_reaction, 1)
active.write_text(a)
