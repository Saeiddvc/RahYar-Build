from pathlib import Path

root = Path(".")

health = root / "app/src/main/java/ir/rahyar/app/core/provider/ProviderHealth.kt"
health.write_text(r'''package ir.rahyar.app.core.provider

enum class ProviderStatus {
    HEALTHY, DEGRADED, UNAVAILABLE, QUOTA_EXHAUSTED, NOT_CONFIGURED
}

data class ProviderHealth(
    val providerId: String,
    val status: ProviderStatus,
    val latencyMs: Long?,
    val quotaRemaining: Int?,
    val lastCheckedAtMillis: Long,
    val failureReason: String? = null
) {
    val isHealthy: Boolean get() = status == ProviderStatus.HEALTHY
}

object ProviderTelemetry {
    const val ORS = "ors"
    const val OSRM = "osrm"
    const val HERE_TRAFFIC = "here_traffic"
    const val OPEN_METEO = "open_meteo"
    const val PHOTON = "photon"
    const val NOMINATIM = "nominatim"

    private val states = linkedMapOf<String, ProviderHealth>()

    @Synchronized
    fun recordSuccess(providerId: String, latencyMs: Long, quotaRemaining: Int? = null, nowMillis: Long = System.currentTimeMillis()) {
        val previous = states[providerId]
        val quota = quotaRemaining ?: previous?.quotaRemaining
        states[providerId] = ProviderHealth(
            providerId,
            if (quota != null && quota <= 0) ProviderStatus.QUOTA_EXHAUSTED else ProviderStatus.HEALTHY,
            latencyMs.coerceAtLeast(0L),
            quota,
            nowMillis,
            null
        )
    }

    @Synchronized
    fun recordFailure(providerId: String, latencyMs: Long?, reason: String?, rateLimited: Boolean = false, nowMillis: Long = System.currentTimeMillis()) {
        val previous = states[providerId]
        states[providerId] = ProviderHealth(
            providerId,
            if (rateLimited) ProviderStatus.QUOTA_EXHAUSTED else ProviderStatus.DEGRADED,
            latencyMs?.coerceAtLeast(0L),
            if (rateLimited) 0 else previous?.quotaRemaining,
            nowMillis,
            reason?.take(180)
        )
    }

    @Synchronized
    fun recordQuota(providerId: String, quotaRemaining: Int?) {
        if (quotaRemaining == null) return
        val previous = states[providerId]
        states[providerId] = ProviderHealth(
            providerId,
            if (quotaRemaining <= 0) ProviderStatus.QUOTA_EXHAUSTED else previous?.status ?: ProviderStatus.HEALTHY,
            previous?.latencyMs,
            quotaRemaining,
            previous?.lastCheckedAtMillis ?: System.currentTimeMillis(),
            previous?.failureReason
        )
    }

    @Synchronized
    fun markNotConfigured(providerId: String, nowMillis: Long = System.currentTimeMillis()) {
        states[providerId] = ProviderHealth(providerId, ProviderStatus.NOT_CONFIGURED, null, null, nowMillis, "not configured")
    }

    @Synchronized fun get(providerId: String): ProviderHealth? = states[providerId]
    @Synchronized fun snapshot(): Map<String, ProviderHealth> = states.toMap()
    @Synchronized fun clearForTests() { states.clear() }
}
''')

instrumentation = root / "app/src/main/java/ir/rahyar/app/core/provider/ProviderInstrumentation.kt"
instrumentation.write_text(r'''package ir.rahyar.app.core.provider

import ir.rahyar.app.data.remote.DirectionsApi
import ir.rahyar.app.data.remote.DirectionsResponse
import ir.rahyar.app.data.remote.TrafficApi
import ir.rahyar.app.data.remote.WeatherApi
import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.TrafficInfo
import ir.rahyar.app.domain.models.TransportMode
import ir.rahyar.app.domain.models.WeatherInfo
import kotlinx.coroutines.CancellationException

class ObservedDirectionsApi(private val providerId: String, private val delegate: DirectionsApi) : DirectionsApi {
    override suspend fun getDirections(origin: LatLng, destination: LatLng, mode: TransportMode, waypoints: List<LatLng>): DirectionsResponse {
        val started = System.nanoTime()
        return try {
            val result = delegate.getDirections(origin, destination, mode, waypoints)
            val elapsed = elapsedMillis(started)
            if (result.routes.isNotEmpty()) ProviderTelemetry.recordSuccess(providerId, elapsed)
            else ProviderTelemetry.recordFailure(providerId, elapsed, "empty route response")
            result
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (t: Throwable) {
            ProviderTelemetry.recordFailure(providerId, elapsedMillis(started), t.message)
            throw t
        }
    }
}

class ObservedTrafficApi(private val providerId: String, private val delegate: TrafficApi) : TrafficApi {
    override suspend fun getTraffic(polyline: List<LatLng>): TrafficInfo {
        val started = System.nanoTime()
        return try {
            val result = delegate.getTraffic(polyline)
            val elapsed = elapsedMillis(started)
            if (result.isLive) ProviderTelemetry.recordSuccess(providerId, elapsed)
            else ProviderTelemetry.recordFailure(providerId, elapsed, "traffic response is not live")
            result
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (t: Throwable) {
            ProviderTelemetry.recordFailure(providerId, elapsedMillis(started), t.message)
            throw t
        }
    }
}

class ObservedWeatherApi(private val providerId: String, private val delegate: WeatherApi) : WeatherApi {
    override suspend fun getWeatherAlong(polyline: List<LatLng>): WeatherInfo {
        val started = System.nanoTime()
        return try {
            val result = delegate.getWeatherAlong(polyline)
            val elapsed = elapsedMillis(started)
            if (result.isLive) ProviderTelemetry.recordSuccess(providerId, elapsed)
            else ProviderTelemetry.recordFailure(providerId, elapsed, "weather response is not live")
            result
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (t: Throwable) {
            ProviderTelemetry.recordFailure(providerId, elapsedMillis(started), t.message)
            throw t
        }
    }
}

private fun elapsedMillis(startedNanos: Long): Long =
    ((System.nanoTime() - startedNanos) / 1_000_000L).coerceAtLeast(0L)
''')

manager = root / "app/src/main/java/ir/rahyar/app/core/provider/ProviderManager.kt"
m = manager.read_text()
if "fun healthSnapshot()" not in m:
    marker = "    fun hasTransitRouting(): Boolean = transitRoutingAvailable\n"
    if marker not in m:
        raise SystemExit("Run47 ProviderManager marker missing")
    m = m.replace(marker, marker + '''    fun healthSnapshot(): Map<String, ProviderHealth> = ProviderTelemetry.snapshot()
    fun providerHealth(providerId: String): ProviderHealth? = ProviderTelemetry.get(providerId)
''', 1)
    manager.write_text(m)

directions = root / "app/src/main/java/ir/rahyar/app/data/remote/DirectionsApi.kt"
d = directions.read_text()
old_endpoint = 'https://api.openrouteservice.org/v2/directions/$profile/json'
new_endpoint = 'https://api.heigit.org/openrouteservice/v2/directions/$profile/json'
if old_endpoint not in d and new_endpoint not in d:
    raise SystemExit("Run47 ORS endpoint target missing")
d = d.replace(old_endpoint, new_endpoint)
if "import ir.rahyar.app.core.provider.ProviderTelemetry" not in d:
    d = d.replace("package ir.rahyar.app.data.remote\n\n", "package ir.rahyar.app.data.remote\n\nimport ir.rahyar.app.core.provider.ProviderTelemetry\n", 1)
old = '''        http.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("ORS HTTP ${response.code}")'''
new = '''        http.newCall(request).execute().use { response ->
            ProviderTelemetry.recordQuota(ProviderTelemetry.ORS, response.header("x-ratelimit-remaining")?.toIntOrNull())
            if (!response.isSuccessful) {
                if (response.code == 429) ProviderTelemetry.recordFailure(ProviderTelemetry.ORS, null, "ORS quota exhausted", rateLimited = true)
                throw IOException("ORS HTTP ${response.code}")
            }'''
if old not in d and "ORS quota exhausted" not in d:
    raise SystemExit("Run47 ORS response target missing")
d = d.replace(old, new, 1)
directions.write_text(d)

traffic = root / "app/src/main/java/ir/rahyar/app/data/remote/TrafficApi.kt"
t = traffic.read_text()
if "import ir.rahyar.app.core.provider.ProviderTelemetry" not in t:
    t = t.replace("package ir.rahyar.app.data.remote\n\n", "package ir.rahyar.app.data.remote\n\nimport ir.rahyar.app.core.provider.ProviderTelemetry\n", 1)
old = '''        http.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("HERE Traffic HTTP ${response.code}")'''
new = '''        http.newCall(request).execute().use { response ->
            ProviderTelemetry.recordQuota(ProviderTelemetry.HERE_TRAFFIC, response.header("x-ratelimit-remaining")?.toIntOrNull())
            if (!response.isSuccessful) {
                if (response.code == 429) ProviderTelemetry.recordFailure(ProviderTelemetry.HERE_TRAFFIC, null, "HERE Traffic quota exhausted", rateLimited = true)
                throw IOException("HERE Traffic HTTP ${response.code}")
            }'''
if old not in t and "HERE Traffic quota exhausted" not in t:
    raise SystemExit("Run47 HERE response target missing")
t = t.replace(old, new, 1)
traffic.write_text(t)

app = root / "app/src/main/java/ir/rahyar/app/di/AppModule.kt"
a = app.read_text()
imports = [
    "import ir.rahyar.app.core.provider.ObservedDirectionsApi\n",
    "import ir.rahyar.app.core.provider.ObservedTrafficApi\n",
    "import ir.rahyar.app.core.provider.ObservedWeatherApi\n",
    "import ir.rahyar.app.core.provider.ProviderTelemetry\n",
]
anchor = "import ir.rahyar.app.core.provider.ProviderManager\n"
for imp in imports:
    if imp not in a:
        if anchor not in a:
            raise SystemExit("Run47 AppModule provider import anchor missing")
        a = a.replace(anchor, anchor + imp, 1)

route_old = '''    fun provideRouteRepository(): RouteRepository {
        val ors = BuildConfig.ORS_API_KEY.takeIf { it.isNotBlank() }?.let { OrsDirectionsApi(http, it) }
        return RouteRepositoryImpl(FallbackDirectionsApi(primary = ors, fallback = OsrmDirectionsApi(http)))
    }'''
route_new = '''    fun provideRouteRepository(): RouteRepository {
        val ors = BuildConfig.ORS_API_KEY.takeIf { it.isNotBlank() }?.let {
            ObservedDirectionsApi(ProviderTelemetry.ORS, OrsDirectionsApi(http, it))
        }
        if (ors == null) ProviderTelemetry.markNotConfigured(ProviderTelemetry.ORS)
        val osrm = ObservedDirectionsApi(ProviderTelemetry.OSRM, OsrmDirectionsApi(http))
        return RouteRepositoryImpl(FallbackDirectionsApi(primary = ors, fallback = osrm))
    }'''
if route_old not in a and "ObservedDirectionsApi(ProviderTelemetry.OSRM" not in a:
    raise SystemExit("Run47 route block missing")
a = a.replace(route_old, route_new, 1)

traffic_old = '''    fun provideTrafficRepository(): TrafficRepository {
        val api: TrafficApi = BuildConfig.HERE_API_KEY.takeIf { it.isNotBlank() }
            ?.let { HereTrafficApi(http, it) }
            ?: UnavailableTrafficApi()
        return TrafficRepositoryImpl(api)
    }'''
traffic_new = '''    fun provideTrafficRepository(): TrafficRepository {
        val configured = BuildConfig.HERE_API_KEY.takeIf { it.isNotBlank() }
        val api: TrafficApi = configured
            ?.let { ObservedTrafficApi(ProviderTelemetry.HERE_TRAFFIC, HereTrafficApi(http, it)) }
            ?: UnavailableTrafficApi().also { ProviderTelemetry.markNotConfigured(ProviderTelemetry.HERE_TRAFFIC) }
        return TrafficRepositoryImpl(api)
    }'''
if traffic_old not in a and "ObservedTrafficApi(ProviderTelemetry.HERE_TRAFFIC" not in a:
    raise SystemExit("Run47 traffic block missing")
a = a.replace(traffic_old, traffic_new, 1)

weather_old = "    fun provideWeatherRepository(): WeatherRepository = WeatherRepositoryImpl(OpenMeteoWeatherApi(http))"
weather_new = '''    fun provideWeatherRepository(): WeatherRepository =
        WeatherRepositoryImpl(ObservedWeatherApi(ProviderTelemetry.OPEN_METEO, OpenMeteoWeatherApi(http)))'''
if weather_old not in a and "ObservedWeatherApi(ProviderTelemetry.OPEN_METEO" not in a:
    raise SystemExit("Run47 weather block missing")
a = a.replace(weather_old, weather_new, 1)
app.write_text(a)

search_repo = root / "app/src/main/java/ir/rahyar/app/data/repository/DestinationSearchRepositoryImpl.kt"
s = search_repo.read_text()
if "import ir.rahyar.app.core.provider.ProviderTelemetry" not in s:
    s = s.replace("import ir.rahyar.app.core.search.rankSearchResults\n", "import ir.rahyar.app.core.search.rankSearchResults\nimport ir.rahyar.app.core.provider.ProviderTelemetry\n", 1)

read_old = '''    private fun readUrl(url: URL, userAgent: String): String {
        val connection = (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 8000
            readTimeout = 8000
            requestMethod = "GET"
            setRequestProperty("User-Agent", userAgent)
            setRequestProperty("Accept", "application/json")
        }
        try {
            if (connection.responseCode !in 200..299) {
                error("Search HTTP ${connection.responseCode}")
            }
            return connection.inputStream.bufferedReader().use { it.readText() }
        } finally {
            connection.disconnect()
        }
    }'''
read_new = '''    private fun readUrl(url: URL, userAgent: String): String {
        val providerId = when {
            url.host.contains("photon", ignoreCase = true) -> ProviderTelemetry.PHOTON
            url.host.contains("nominatim", ignoreCase = true) -> ProviderTelemetry.NOMINATIM
            else -> url.host
        }
        val started = System.nanoTime()
        val connection = (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 8000
            readTimeout = 8000
            requestMethod = "GET"
            setRequestProperty("User-Agent", userAgent)
            setRequestProperty("Accept", "application/json")
        }
        try {
            val code = connection.responseCode
            val elapsed = ((System.nanoTime() - started) / 1_000_000L).coerceAtLeast(0L)
            if (code !in 200..299) {
                ProviderTelemetry.recordFailure(providerId, elapsed, "Search HTTP $code", rateLimited = code == 429)
                error("Search HTTP $code")
            }
            ProviderTelemetry.recordSuccess(providerId, elapsed)
            return connection.inputStream.bufferedReader().use { it.readText() }
        } finally {
            connection.disconnect()
        }
    }'''
if read_old not in s and "val providerId = when {" not in s:
    raise SystemExit("Run47 search telemetry target missing")
s = s.replace(read_old, read_new, 1)
search_repo.write_text(s)

provider_test = root / "app/src/test/java/ir/rahyar/app/core/provider/ProviderTelemetryTest.kt"
provider_test.parent.mkdir(parents=True, exist_ok=True)
provider_test.write_text(r'''package ir.rahyar.app.core.provider

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class ProviderTelemetryTest {
    @After fun cleanup() = ProviderTelemetry.clearForTests()

    @Test fun successTracksLatencyAndQuota() {
        ProviderTelemetry.recordSuccess(ProviderTelemetry.ORS, 123L, 17, 1000L)
        val health = ProviderTelemetry.get(ProviderTelemetry.ORS)
        assertNotNull(health)
        assertEquals(ProviderStatus.HEALTHY, health?.status)
        assertEquals(123L, health?.latencyMs)
        assertEquals(17, health?.quotaRemaining)
    }

    @Test fun zeroQuotaIsNeverReportedHealthy() {
        ProviderTelemetry.recordSuccess(ProviderTelemetry.ORS, 80L, 0)
        assertEquals(ProviderStatus.QUOTA_EXHAUSTED, ProviderTelemetry.get(ProviderTelemetry.ORS)?.status)
    }

    @Test fun missingCredentialIsExplicitNotConfigured() {
        ProviderTelemetry.markNotConfigured(ProviderTelemetry.HERE_TRAFFIC)
        assertEquals(ProviderStatus.NOT_CONFIGURED, ProviderTelemetry.get(ProviderTelemetry.HERE_TRAFFIC)?.status)
    }

    @Test fun failureIsDegradedAndKeepsReason() {
        ProviderTelemetry.recordFailure(ProviderTelemetry.PHOTON, 420L, "timeout")
        val health = ProviderTelemetry.get(ProviderTelemetry.PHOTON)
        assertEquals(ProviderStatus.DEGRADED, health?.status)
        assertEquals("timeout", health?.failureReason)
    }
}
''')

fallback_test = root / "app/src/test/java/ir/rahyar/app/data/remote/FallbackDirectionsApiTest.kt"
fallback_test.parent.mkdir(parents=True, exist_ok=True)
fallback_test.write_text(r'''package ir.rahyar.app.data.remote

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.TransportMode
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.LocalDateTime

class FallbackDirectionsApiTest {
    @Test fun osrmFallbackRunsWhenPrimaryFails() = runBlocking {
        val primary = object : DirectionsApi {
            override suspend fun getDirections(origin: LatLng, destination: LatLng, mode: TransportMode, waypoints: List<LatLng>): DirectionsResponse =
                error("primary unavailable")
        }
        val fallback = object : DirectionsApi {
            override suspend fun getDirections(origin: LatLng, destination: LatLng, mode: TransportMode, waypoints: List<LatLng>): DirectionsResponse =
                DirectionsResponse(listOf(DirectionsRoute("fallback-route", listOf(origin, destination), 12, 4.0, LocalDateTime.now())))
        }
        val result = FallbackDirectionsApi(primary, fallback).getDirections(
            LatLng(35.83, 50.95), LatLng(35.82, 51.00), TransportMode.CAR
        )
        assertEquals("fallback-route", result.routes.single().id)
    }
}
''')

integrity_test = root / "app/src/test/java/ir/rahyar/app/data/remote/ProviderIntegrityTest.kt"
integrity_test.write_text(r'''package ir.rahyar.app.data.remote

import ir.rahyar.app.core.weather.buildWeatherInfoFromSnapshots
import ir.rahyar.app.domain.models.LatLng
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProviderIntegrityTest {
    @Test fun unavailableTrafficDoesNotFabricateLiveTraffic() = runBlocking {
        val info = UnavailableTrafficApi().getTraffic(listOf(LatLng(35.83, 50.95), LatLng(35.82, 51.00)))
        assertFalse(info.isLive)
        assertTrue(info.segments.isEmpty())
    }

    @Test fun missingWeatherSamplesDoNotFabricateLiveWeather() {
        val info = buildWeatherInfoFromSnapshots(emptyList())
        assertFalse(info.isLive)
        assertTrue(info.timeline.isEmpty())
        assertTrue(info.alerts.isEmpty())
    }
}
''')
