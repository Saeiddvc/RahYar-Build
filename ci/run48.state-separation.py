from pathlib import Path

root = Path(".")

core = root / "app/src/main/java/ir/rahyar/app/core/navigation/JourneySeparation.kt"
core.parent.mkdir(parents=True, exist_ok=True)
core.write_text("""package ir.rahyar.app.core.navigation

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.Route
import ir.rahyar.app.navigation.TracePoint
import ir.rahyar.app.navigation.TripTrace
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

data class RouteSummary(
    val routeId: String,
    val plannedDistanceKm: Double,
    val plannedDurationMinutes: Int
)

data class TripSummary(
    val pointCount: Int,
    val actualDistanceMeters: Double,
    val actualDurationMillis: Long,
    val averageSpeedKmh: Double,
    val maxSpeedKmh: Double
)

data class TripStoryPayload(
    val tracePoints: List<TracePoint>,
    val summary: TripSummary
)

fun buildRouteSummary(route: Route): RouteSummary =
    RouteSummary(
        routeId = route.id,
        plannedDistanceKm = route.distanceKm,
        plannedDurationMinutes = route.durationMinutes
    )

fun buildTripSummary(trace: TripTrace): TripSummary? {
    if (trace.points.size < 2) return null
    val points = trace.points.sortedBy { it.timestampMillis }
    val actualDistance = points.zipWithNext().sumOf { (a, b) ->
        distanceMeters(a.location, b.location)
    }
    val duration = (points.last().timestampMillis - points.first().timestampMillis).coerceAtLeast(0L)
    return TripSummary(
        pointCount = points.size,
        actualDistanceMeters = actualDistance,
        actualDurationMillis = duration,
        averageSpeedKmh = points.map { it.speedKmh.coerceAtLeast(0.0) }.average(),
        maxSpeedKmh = points.maxOf { it.speedKmh.coerceAtLeast(0.0) }
    )
}

fun buildTripStoryPayload(trace: TripTrace): TripStoryPayload? {
    val summary = buildTripSummary(trace) ?: return null
    return TripStoryPayload(
        tracePoints = trace.points.toList(),
        summary = summary
    )
}

private fun distanceMeters(a: LatLng, b: LatLng): Double {
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

test = root / "app/src/test/java/ir/rahyar/app/core/navigation/JourneySeparationTest.kt"
test.parent.mkdir(parents=True, exist_ok=True)
test.write_text("""package ir.rahyar.app.core.navigation

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.Route
import ir.rahyar.app.domain.models.RouteType
import ir.rahyar.app.domain.models.TransportMode
import ir.rahyar.app.navigation.NavigationSession
import ir.rahyar.app.navigation.NavigationState
import ir.rahyar.app.navigation.TracePoint
import ir.rahyar.app.navigation.TripTrace
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDateTime

class JourneySeparationTest {
    private fun route(id: String = "planned", distanceKm: Double = 88.0, durationMinutes: Int = 90) = Route(
        id = id,
        type = RouteType.RECOMMENDED,
        points = listOf(LatLng(35.80, 50.95), LatLng(35.70, 51.40)),
        durationMinutes = durationMinutes,
        distanceKm = distanceKm,
        eta = LocalDateTime.now(),
        transportMode = TransportMode.CAR
    )

    private fun trace(): TripTrace = TripTrace(
        listOf(
            TracePoint(LatLng(35.7000, 51.4000), 1_000L, 40.0, 90f),
            TracePoint(LatLng(35.7010, 51.4000), 6_000L, 55.0, 0f),
            TracePoint(LatLng(35.7020, 51.4000), 11_000L, 50.0, 0f)
        )
    )

    @Test fun routeSummaryComesOnlyFromRoute() {
        val summary = buildRouteSummary(route(distanceKm = 88.0, durationMinutes = 90))
        assertEquals("planned", summary.routeId)
        assertEquals(88.0, summary.plannedDistanceKm, 0.001)
        assertEquals(90, summary.plannedDurationMinutes)
    }

    @Test fun tripSummaryComesOnlyFromTripTrace() {
        val summary = buildTripSummary(trace())
        assertNotNull(summary)
        assertEquals(3, summary?.pointCount)
        assertTrue((summary?.actualDistanceMeters ?: 0.0) > 150.0)
        assertEquals(10_000L, summary?.actualDurationMillis)
    }

    @Test fun noStoryExistsWithoutRealTripTrace() {
        assertNull(buildTripStoryPayload(TripTrace()))
        assertNull(buildTripStoryPayload(TripTrace(listOf(TracePoint(LatLng(35.7, 51.4), 1_000L, 0.0, 0f)))))
    }

    @Test fun tripStoryBuilderAcceptsTripTraceNotRoute() {
        val method = Class.forName("ir.rahyar.app.core.navigation.JourneySeparationKt")
            .declaredMethods
            .first { it.name == "buildTripStoryPayload" }
        assertEquals(1, method.parameterTypes.size)
        assertEquals("ir.rahyar.app.navigation.TripTrace", method.parameterTypes.single().name)
    }

    @Test fun summaryBuildersHaveNoSharedSourceOfTruth() {
        val methods = Class.forName("ir.rahyar.app.core.navigation.JourneySeparationKt").declaredMethods
        val routeMethod = methods.first { it.name == "buildRouteSummary" }
        val tripMethod = methods.first { it.name == "buildTripSummary" }
        assertEquals("ir.rahyar.app.domain.models.Route", routeMethod.parameterTypes.single().name)
        assertEquals("ir.rahyar.app.navigation.TripTrace", tripMethod.parameterTypes.single().name)
    }

    @Test fun rerouteChangesRouteWithoutResettingSessionOrTrace() {
        val session = NavigationSession()
        session.setOrigin(LatLng(35.70, 51.40))
        session.setDestination(LatLng(35.75, 51.45))
        session.beginNavigation(route("r1", 10.0, 20))
        session.appendTracePoint(TracePoint(LatLng(35.7000, 51.4000), 1_000L, 30.0, 0f))
        session.appendTracePoint(TracePoint(LatLng(35.7010, 51.4010), 2_000L, 35.0, 45f))

        val before = session.state.value
        val sessionId = before.sessionId
        val traceBefore = before.tripTrace

        session.selectRoute(route("r2", 9.0, 18))
        val after = session.state.value

        assertTrue(after.navigationState is NavigationState.Navigating)
        assertEquals(sessionId, after.sessionId)
        assertEquals(traceBefore, after.tripTrace)
        assertEquals("r2", after.selectedRoute?.id)
    }

    @Test fun storyPayloadCopiesTraceListAndDoesNotShareMutableList() {
        val mutable = mutableListOf(
            TracePoint(LatLng(35.7000, 51.4000), 1_000L, 30.0, 0f),
            TracePoint(LatLng(35.7010, 51.4000), 2_000L, 35.0, 0f)
        )
        val payload = buildTripStoryPayload(TripTrace(mutable))
        assertNotNull(payload)
        mutable.clear()
        assertEquals(2, payload?.tracePoints?.size)
    }
}
""")

active = root / "app/src/main/java/ir/rahyar/app/ui/screens/ActiveNavigationScreen.kt"
text = active.read_text()

if "import ir.rahyar.app.core.navigation.buildTripStoryPayload" not in text:
    anchor = "import ir.rahyar.app.core.navigation.NavigationHudState\n"
    if anchor not in text:
        raise SystemExit("Run48 navigation import anchor missing")
    text = text.replace(anchor, anchor + "import ir.rahyar.app.core.navigation.buildTripStoryPayload\n", 1)

# Trip Story entry must be trace-derived. Route is deliberately not passed to the story sheet.
text = text.replace(
    """    if (showTripStory) {
        val trace = session.tripTrace.points
        TripStorySheet(
            route = initialRoute,
            trace = trace,""",
    """    if (showTripStory) {
        val storyPayload = buildTripStoryPayload(session.tripTrace)
        val trace = storyPayload?.tracePoints.orEmpty()
        TripStorySheet(
            trace = trace,""",
    1
)

text = text.replace(
    """private fun TripStorySheet(
    route: Route,
    trace: List<ir.rahyar.app.navigation.TracePoint>,""",
    """private fun TripStorySheet(
    trace: List<ir.rahyar.app.navigation.TracePoint>,""",
    1
)

active.write_text(text)
