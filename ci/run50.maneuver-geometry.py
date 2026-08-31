from pathlib import Path

root = Path(".")

geometry = root / "app/src/main/java/ir/rahyar/app/core/navigation/ManeuverGeometry.kt"
geometry.write_text("""package ir.rahyar.app.core.navigation

import ir.rahyar.app.domain.models.LatLng
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

data class RouteProgress(
    val segmentIndex: Int,
    val fractionOnSegment: Double,
    val metersFromRouteStart: Double,
    val distanceFromRouteMeters: Double
)

fun routeProgressAt(
    points: List<LatLng>,
    location: LatLng,
    startSegmentIndex: Int = 0
): RouteProgress? {
    if (points.size < 2) return null
    val firstSegment = startSegmentIndex.coerceIn(0, points.lastIndex - 1)

    val cumulative = DoubleArray(points.size)
    for (i in 0 until points.lastIndex) {
        cumulative[i + 1] = cumulative[i] + geoDistanceMeters(points[i], points[i + 1])
    }

    var best: RouteProgress? = null
    for (i in firstSegment until points.lastIndex) {
        val fraction = projectionFraction(location, points[i], points[i + 1])
        val projected = interpolate(points[i], points[i + 1], fraction)
        val distanceFromRoute = geoDistanceMeters(location, projected)
        val segmentMeters = geoDistanceMeters(points[i], points[i + 1])
        val progress = cumulative[i] + segmentMeters * fraction
        val candidate = RouteProgress(i, fraction, progress, distanceFromRoute)
        if (best == null || candidate.distanceFromRouteMeters < best!!.distanceFromRouteMeters) {
            best = candidate
        }
    }
    return best
}

fun distanceAlongRouteToLocationMeters(
    points: List<LatLng>,
    currentSnapped: LatLng,
    currentSegmentIndex: Int,
    targetLocation: LatLng
): Double? {
    if (points.size < 2 || currentSegmentIndex !in 0 until points.lastIndex) return null

    val currentProgress = routeProgressAt(
        points = points,
        location = currentSnapped,
        startSegmentIndex = currentSegmentIndex
    ) ?: return null

    val targetProgress = routeProgressAt(
        points = points,
        location = targetLocation,
        startSegmentIndex = currentSegmentIndex
    ) ?: return null

    val delta = targetProgress.metersFromRouteStart - currentProgress.metersFromRouteStart
    return delta.takeIf { it >= -1.0 }?.coerceAtLeast(0.0)
}

private fun projectionFraction(point: LatLng, start: LatLng, end: LatLng): Double {
    val referenceLatitude = Math.toRadians((start.latitude + end.latitude + point.latitude) / 3.0)
    val longitudeScale = cos(referenceLatitude).coerceAtLeast(0.01)

    val ax = start.longitude * longitudeScale
    val ay = start.latitude
    val bx = end.longitude * longitudeScale
    val by = end.latitude
    val px = point.longitude * longitudeScale
    val py = point.latitude

    val dx = bx - ax
    val dy = by - ay
    val lengthSquared = dx * dx + dy * dy
    if (lengthSquared <= 1e-16) return 0.0
    return (((px - ax) * dx + (py - ay) * dy) / lengthSquared).coerceIn(0.0, 1.0)
}

private fun interpolate(start: LatLng, end: LatLng, fraction: Double): LatLng =
    LatLng(
        latitude = start.latitude + (end.latitude - start.latitude) * fraction,
        longitude = start.longitude + (end.longitude - start.longitude) * fraction
    )

private fun geoDistanceMeters(a: LatLng, b: LatLng): Double {
    val radius = 6_371_000.0
    val dLat = Math.toRadians(b.latitude - a.latitude)
    val dLon = Math.toRadians(b.longitude - a.longitude)
    val lat1 = Math.toRadians(a.latitude)
    val lat2 = Math.toRadians(b.latitude)
    val h = sin(dLat / 2) * sin(dLat / 2) +
        cos(lat1) * cos(lat2) * sin(dLon / 2) * sin(dLon / 2)
    return radius * 2 * atan2(sqrt(h), sqrt(1 - h))
}
""")

test = root / "app/src/test/java/ir/rahyar/app/core/navigation/ManeuverGeometryTest.kt"
test.parent.mkdir(parents=True, exist_ok=True)
test.write_text("""package ir.rahyar.app.core.navigation

import ir.rahyar.app.domain.models.LatLng
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ManeuverGeometryTest {
    @Test fun straightRouteMeasuresFromCurrentProjectedPositionToManeuver() {
        val points = listOf(
            LatLng(35.7000, 51.4000),
            LatLng(35.7000, 51.4010),
            LatLng(35.7000, 51.4020)
        )
        val current = LatLng(35.7000, 51.4005)
        val target = LatLng(35.7000, 51.4015)

        val meters = distanceAlongRouteToLocationMeters(points, current, 0, target)

        assertNotNull(meters)
        assertTrue(meters!! in 85.0..100.0)
    }

    @Test fun turnGeometrySumsBothPolylineLegsNotAirDistance() {
        val points = listOf(
            LatLng(35.7000, 51.4000),
            LatLng(35.7000, 51.4010),
            LatLng(35.7010, 51.4010)
        )
        val current = LatLng(35.7000, 51.4005)
        val target = LatLng(35.7005, 51.4010)

        val meters = distanceAlongRouteToLocationMeters(points, current, 0, target)

        assertNotNull(meters)
        assertTrue(meters!! in 95.0..115.0)
    }

    @Test fun targetBehindCurrentIsNotReportedAsUpcomingManeuver() {
        val points = listOf(
            LatLng(35.7000, 51.4000),
            LatLng(35.7000, 51.4010),
            LatLng(35.7000, 51.4020)
        )
        val current = LatLng(35.7000, 51.4015)
        val behind = LatLng(35.7000, 51.4005)

        assertNull(distanceAlongRouteToLocationMeters(points, current, 1, behind))
    }

    @Test fun exactCurrentManeuverReportsZeroInsteadOfNegativeDistance() {
        val points = listOf(
            LatLng(35.7000, 51.4000),
            LatLng(35.7000, 51.4010)
        )
        val current = LatLng(35.7000, 51.4005)
        val meters = distanceAlongRouteToLocationMeters(points, current, 0, current)
        assertEquals(0.0, meters ?: -1.0, 1.0)
    }
}
""")

engine = root / "app/src/main/java/ir/rahyar/app/core/navigation/NavigationEngine.kt"
e = engine.read_text()

old = """        val candidate = route.steps
            .map { step -> step to nearestPointIndex(route, step.location) }
            .filter { (_, index) -> index >= match.segmentIndex }
            .minByOrNull { (_, index) -> index }
            ?: return null

        val (step, targetIndex) = candidate
        return NextManeuver(
            instruction = step.instruction.ifBlank { "ادامه مسیر" },
            maneuverType = step.maneuverType,
            distanceMeters = distanceToPointAlongRouteMeters(route, match, targetIndex)
        )"""

new = """        val candidate = route.steps
            .mapNotNull { step ->
                distanceAlongRouteToLocationMeters(
                    points = route.points,
                    currentSnapped = match.snapped,
                    currentSegmentIndex = match.segmentIndex,
                    targetLocation = step.location
                )?.let { distance -> step to distance }
            }
            .minByOrNull { (_, distance) -> distance }
            ?: return null

        val (step, maneuverDistanceMeters) = candidate
        return NextManeuver(
            instruction = step.instruction.ifBlank { "ادامه مسیر" },
            maneuverType = step.maneuverType,
            distanceMeters = maneuverDistanceMeters
        )"""

if old not in e:
    raise SystemExit("Run50 nextManeuver geometry target not found")
e = e.replace(old, new, 1)
engine.write_text(e)
