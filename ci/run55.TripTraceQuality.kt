package ir.rahyar.app.core.navigation

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.navigation.TracePoint
import ir.rahyar.app.navigation.TripTrace
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

private const val MAX_STORY_ACCURACY_METERS = 40f
private const val MAX_PLAUSIBLE_SPEED_MPS = 70.0
private const val STATIONARY_SPEED_KMH = 5.0
private const val MIN_STATIONARY_MOVEMENT_METERS = 5.0
private const val MIN_REAL_TRIP_DISTANCE_METERS = 100.0
private const val MIN_REAL_TRIP_DURATION_MILLIS = 30_000L
private const val MIN_REAL_TRIP_POINTS = 3

fun shouldAcceptTracePoint(previous: TracePoint?, candidate: TracePoint): Boolean {
    val accuracy = candidate.accuracyMeters
    if (accuracy != null && (!accuracy.isFinite() || accuracy > MAX_STORY_ACCURACY_METERS)) {
        return false
    }
    if (previous == null) return true

    val dtMillis = candidate.timestampMillis - previous.timestampMillis
    if (dtMillis <= 0L) return false

    val distance = traceDistanceMeters(previous.location, candidate.location)
    val impliedSpeedMps = distance / (dtMillis / 1000.0)
    if (!impliedSpeedMps.isFinite() || impliedSpeedMps > MAX_PLAUSIBLE_SPEED_MPS) {
        return false
    }

    val uncertaintyFloor = maxOf(
        MIN_STATIONARY_MOVEMENT_METERS,
        (((previous.accuracyMeters ?: 0f) + (candidate.accuracyMeters ?: 0f)) * 0.12f).toDouble()
    )
    if (
        distance < uncertaintyFloor &&
        previous.speedKmh < STATIONARY_SPEED_KMH &&
        candidate.speedKmh < STATIONARY_SPEED_KMH
    ) {
        return false
    }
    return true
}

fun qualityFilteredTripTrace(trace: TripTrace): TripTrace {
    if (trace.points.isEmpty()) return TripTrace()
    val accepted = mutableListOf<TracePoint>()
    trace.points.sortedBy { it.timestampMillis }.forEach { point ->
        if (shouldAcceptTracePoint(accepted.lastOrNull(), point)) accepted += point
    }
    return TripTrace(accepted)
}

fun isMeaningfulRealTrip(trace: TripTrace): Boolean {
    val filtered = qualityFilteredTripTrace(trace)
    if (filtered.points.size < MIN_REAL_TRIP_POINTS) return false
    val duration = filtered.points.last().timestampMillis - filtered.points.first().timestampMillis
    if (duration < MIN_REAL_TRIP_DURATION_MILLIS) return false
    val distance = filtered.points.zipWithNext().sumOf { (a, b) ->
        traceDistanceMeters(a.location, b.location)
    }
    return distance >= MIN_REAL_TRIP_DISTANCE_METERS
}

fun traceDistanceMeters(a: LatLng, b: LatLng): Double {
    val radius = 6_371_000.0
    val dLat = Math.toRadians(b.latitude - a.latitude)
    val dLon = Math.toRadians(b.longitude - a.longitude)
    val lat1 = Math.toRadians(a.latitude)
    val lat2 = Math.toRadians(b.latitude)
    val h = sin(dLat / 2) * sin(dLat / 2) +
        cos(lat1) * cos(lat2) * sin(dLon / 2) * sin(dLon / 2)
    return radius * 2 * atan2(sqrt(h), sqrt(1 - h))
}
