package ir.rahyar.app.core.navigation

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.TrafficInfo
import ir.rahyar.app.domain.models.TrafficLevel
import ir.rahyar.app.domain.models.TripMediaType
import ir.rahyar.app.domain.models.WeatherHazard
import ir.rahyar.app.domain.models.WeatherInfo
import ir.rahyar.app.navigation.TripTrace
import kotlin.math.floor

enum class TripStoryViewMode { DRIVER, AERIAL, OVERVIEW }

enum class TripStoryTimelineKind { WEATHER, TRAFFIC, MEDIA, STOP }

enum class TripStoryEffectKind { RAIN, SNOW, FOG, HEAVY_TRAFFIC, MEDIA_MOMENT }

data class TripStoryWeatherEvent(
    val timestampMillis: Long,
    val location: LatLng,
    val summary: String,
    val temperatureC: Int,
    val precipitationMm: Double,
    val hazards: Set<WeatherHazard>
)

data class TripStoryTrafficEvent(
    val timestampMillis: Long,
    val location: LatLng,
    val level: TrafficLevel,
    val jamFactor: Double?
)

data class TripStoryMediaEvent(
    val id: String,
    val uri: String,
    val timestampMillis: Long,
    val location: LatLng,
    val type: TripMediaType
)

data class TripStoryStopEvent(
    val id: String,
    val timestampMillis: Long,
    val location: LatLng
)

data class TripStoryRuntimeData(
    val tripId: String,
    val trace: TripTrace,
    val weatherTimeline: List<TripStoryWeatherEvent>,
    val trafficTimeline: List<TripStoryTrafficEvent>,
    val mediaTimeline: List<TripStoryMediaEvent>,
    val stopTimeline: List<TripStoryStopEvent>,
    val actualDistanceMeters: Double,
    val actualDurationMillis: Long,
    val averageSpeedKmh: Double,
    val maxSpeedKmh: Double
)

data class TripStoryTimelineItem(
    val kind: TripStoryTimelineKind,
    val timestampMillis: Long,
    val location: LatLng,
    val description: String,
    val mediaUri: String? = null
)

data class TripStoryMotionFrame(
    val mode: TripStoryViewMode,
    val timestampMillis: Long,
    val target: LatLng,
    val bearing: Float,
    val zoom: Double,
    val tilt: Double,
    val traceIndex: Int
)

class TripStoryRecorder {
    private val weatherEvents = mutableListOf<TripStoryWeatherEvent>()
    private val trafficEvents = mutableListOf<TripStoryTrafficEvent>()
    private val mediaEvents = mutableListOf<TripStoryMediaEvent>()
    private val stopEvents = mutableListOf<TripStoryStopEvent>()

    fun recordWeather(info: WeatherInfo, timestampMillis: Long) {
        if (!info.isLive) return
        info.timeline.forEach { item ->
            val event = TripStoryWeatherEvent(
                timestampMillis = timestampMillis,
                location = item.location,
                summary = info.summary,
                temperatureC = item.temperatureC,
                precipitationMm = item.precipitationMm,
                hazards = item.hazards
            )
            if (weatherEvents.none {
                    it.timestampMillis == event.timestampMillis &&
                        it.location == event.location &&
                        it.temperatureC == event.temperatureC &&
                        it.hazards == event.hazards
                }) {
                weatherEvents += event
            }
        }
    }

    fun recordTraffic(info: TrafficInfo, timestampMillis: Long) {
        if (!info.isLive) return
        info.segments.forEach { segment ->
            val event = TripStoryTrafficEvent(
                timestampMillis = timestampMillis,
                location = segment.start,
                level = segment.level,
                jamFactor = segment.jamFactor
            )
            if (trafficEvents.none {
                    it.timestampMillis == event.timestampMillis &&
                        it.location == event.location &&
                        it.level == event.level &&
                        it.jamFactor == event.jamFactor
                }) {
                trafficEvents += event
            }
        }
    }

    fun recordMedia(
        uri: String,
        type: TripMediaType,
        timestampMillis: Long,
        location: LatLng
    ): Boolean {
        if (uri.isBlank()) return false
        val id = "media-" + timestampMillis + "-" + mediaEvents.size
        mediaEvents += TripStoryMediaEvent(id, uri, timestampMillis, location, type)
        return true
    }

    fun recordStop(id: String, timestampMillis: Long, location: LatLng) {
        if (stopEvents.none { it.id == id }) {
            stopEvents += TripStoryStopEvent(id, timestampMillis, location)
        }
    }

    fun build(trace: TripTrace, tripId: String? = null): TripStoryRuntimeData? {
        val summary = buildTripSummary(trace) ?: return null
        val sortedTrace = TripTrace(trace.points.sortedBy { it.timestampMillis })
        return TripStoryRuntimeData(
            tripId = tripId ?: ("trip-" + sortedTrace.points.first().timestampMillis),
            trace = sortedTrace,
            weatherTimeline = weatherEvents.sortedBy { it.timestampMillis }.toList(),
            trafficTimeline = trafficEvents.sortedBy { it.timestampMillis }.toList(),
            mediaTimeline = mediaEvents.sortedBy { it.timestampMillis }.toList(),
            stopTimeline = stopEvents.sortedBy { it.timestampMillis }.toList(),
            actualDistanceMeters = summary.actualDistanceMeters,
            actualDurationMillis = summary.actualDurationMillis,
            averageSpeedKmh = summary.averageSpeedKmh,
            maxSpeedKmh = summary.maxSpeedKmh
        )
    }
}

fun buildTripStoryTimeline(data: TripStoryRuntimeData): List<TripStoryTimelineItem> =
    buildList {
        data.weatherTimeline.forEach { event ->
            add(
                TripStoryTimelineItem(
                    TripStoryTimelineKind.WEATHER,
                    event.timestampMillis,
                    event.location,
                    "آب‌وهوا: " + event.summary + "، " + event.temperatureC + "°"
                )
            )
        }
        data.trafficTimeline.forEach { event ->
            add(
                TripStoryTimelineItem(
                    TripStoryTimelineKind.TRAFFIC,
                    event.timestampMillis,
                    event.location,
                    "ترافیک واقعی: " + event.level.name
                )
            )
        }
        data.mediaTimeline.forEach { event ->
            add(
                TripStoryTimelineItem(
                    TripStoryTimelineKind.MEDIA,
                    event.timestampMillis,
                    event.location,
                    if (event.type == TripMediaType.PHOTO) "عکس ثبت‌شده در سفر" else "ویدئوی ثبت‌شده در سفر",
                    mediaUri = event.uri
                )
            )
        }
        data.stopTimeline.forEach { event ->
            add(
                TripStoryTimelineItem(
                    TripStoryTimelineKind.STOP,
                    event.timestampMillis,
                    event.location,
                    "توقف واقعی در مسیر"
                )
            )
        }
    }.sortedBy { it.timestampMillis }

fun tripStoryEffectsAt(
    data: TripStoryRuntimeData,
    timestampMillis: Long,
    windowMillis: Long = 120_000L
): Set<TripStoryEffectKind> {
    val effects = linkedSetOf<TripStoryEffectKind>()
    data.weatherTimeline
        .filter { kotlin.math.abs(it.timestampMillis - timestampMillis) <= windowMillis }
        .forEach { event ->
            if (WeatherHazard.RAIN in event.hazards) effects += TripStoryEffectKind.RAIN
            if (WeatherHazard.SNOW in event.hazards) effects += TripStoryEffectKind.SNOW
            if (WeatherHazard.FOG in event.hazards) effects += TripStoryEffectKind.FOG
        }
    if (data.trafficTimeline.any {
            kotlin.math.abs(it.timestampMillis - timestampMillis) <= windowMillis &&
                it.level == TrafficLevel.HEAVY
        }) {
        effects += TripStoryEffectKind.HEAVY_TRAFFIC
    }
    if (data.mediaTimeline.any {
            kotlin.math.abs(it.timestampMillis - timestampMillis) <= 30_000L
        }) {
        effects += TripStoryEffectKind.MEDIA_MOMENT
    }
    return effects
}

fun tripStoryMotionFrame(
    data: TripStoryRuntimeData,
    mode: TripStoryViewMode,
    progress: Float
): TripStoryMotionFrame? {
    val points = data.trace.points
    if (points.size < 2) return null
    val p = progress.coerceIn(0f, 1f)
    val index = floor(p * points.lastIndex).toInt().coerceIn(0, points.lastIndex)
    val current = points[index]
    return when (mode) {
        TripStoryViewMode.DRIVER -> TripStoryMotionFrame(
            mode = mode,
            timestampMillis = current.timestampMillis,
            target = current.location,
            bearing = current.heading,
            zoom = 17.4,
            tilt = 56.0,
            traceIndex = index
        )
        TripStoryViewMode.AERIAL -> TripStoryMotionFrame(
            mode = mode,
            timestampMillis = current.timestampMillis,
            target = current.location,
            bearing = 0f,
            zoom = 14.6,
            tilt = 35.0,
            traceIndex = index
        )
        TripStoryViewMode.OVERVIEW -> TripStoryMotionFrame(
            mode = mode,
            timestampMillis = current.timestampMillis,
            target = LatLng(
                latitude = points.map { it.location.latitude }.average(),
                longitude = points.map { it.location.longitude }.average()
            ),
            bearing = 0f,
            zoom = 11.8,
            tilt = 0.0,
            traceIndex = index
        )
    }
}

fun tripStoryVisibleTrace(
    data: TripStoryRuntimeData,
    mode: TripStoryViewMode,
    progress: Float
): List<LatLng> {
    val points = data.trace.points
    if (points.size < 2) return emptyList()
    val frame = tripStoryMotionFrame(data, mode, progress) ?: return emptyList()
    val range = when (mode) {
        TripStoryViewMode.DRIVER ->
            (frame.traceIndex - 12).coerceAtLeast(0)..(frame.traceIndex + 8).coerceAtMost(points.lastIndex)
        TripStoryViewMode.AERIAL ->
            (frame.traceIndex - 60).coerceAtLeast(0)..(frame.traceIndex + 24).coerceAtMost(points.lastIndex)
        TripStoryViewMode.OVERVIEW -> 0..points.lastIndex
    }
    return range.map { points[it].location }
}
