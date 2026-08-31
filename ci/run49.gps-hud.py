from pathlib import Path

root = Path(".")

policy = root / "app/src/main/java/ir/rahyar/app/core/navigation/NavigationPresentationPolicy.kt"
policy.write_text("""package ir.rahyar.app.core.navigation

import ir.rahyar.app.domain.models.MapViewMode
import kotlin.math.max

fun offRouteConfirmationsRequired(decision: OffRouteDecision, speedMps: Double): Int =
    if (decision.severe || speedMps >= 15.0) 1 else 2

fun displaySpeedKmh(fusedSpeedMps: Double): Double =
    (fusedSpeedMps.coerceAtLeast(0.0) * 3.6)

fun estimateRemainingMinutes(
    plannedDurationMinutes: Int,
    plannedDistanceKm: Double,
    remainingDistanceKm: Double
): Int {
    if (plannedDurationMinutes <= 0 || plannedDistanceKm <= 0.0) return 1
    val fraction = (remainingDistanceKm / plannedDistanceKm).coerceIn(0.0, 1.0)
    return max(1, (plannedDurationMinutes * fraction).toInt())
}

fun lookAheadMetersForSpeed(speedKmh: Double): Double {
    val speedMps = speedKmh.coerceAtLeast(0.0) / 3.6
    return (32.0 + speedMps * 4.2).coerceIn(32.0, 115.0)
}

fun cameraBearingForMode(mode: MapViewMode, vehicleBearing: Float): Double = when (mode) {
    MapViewMode.NORTH_UP -> 0.0
    MapViewMode.HEADING_UP, MapViewMode.THREE_D -> vehicleBearing.toDouble()
}

fun naturalPersianManeuver(instruction: String): String {
    val raw = instruction.trim()
    if (raw.isBlank()) return "ادامه مسیر"
    val lower = raw.lowercase()
    return when {
        "uturn" in lower || "u-turn" in lower || "make a u turn" in lower -> "دور بزنید"
        "roundabout" in lower && ("first" in lower || "1st" in lower) -> "در میدان از خروجی اول خارج شوید"
        "roundabout" in lower && ("second" in lower || "2nd" in lower) -> "در میدان از خروجی دوم خارج شوید"
        "roundabout" in lower && ("third" in lower || "3rd" in lower) -> "در میدان از خروجی سوم خارج شوید"
        "turn sharp left" in lower -> "به چپ تند بپیچید"
        "turn sharp right" in lower -> "به راست تند بپیچید"
        "turn left" in lower || "keep left" in lower -> "به چپ بپیچید"
        "turn right" in lower || "keep right" in lower -> "به راست بپیچید"
        "continue" in lower || "straight" in lower -> "مستقیم ادامه دهید"
        "arrive" in lower || "destination" in lower -> "به مقصد رسیدید"
        else -> raw
    }
}
""")

test = root / "app/src/test/java/ir/rahyar/app/core/navigation/NavigationPresentationPolicyTest.kt"
test.parent.mkdir(parents=True, exist_ok=True)
test.write_text("""package ir.rahyar.app.core.navigation

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.MapViewMode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class NavigationPresentationPolicyTest {
    @Test fun severeOffRouteReroutesOnFirstConfirmedFix() {
        val decision = OffRouteDecision(candidate = true, severe = true, thresholdMeters = 30.0)
        assertEquals(1, offRouteConfirmationsRequired(decision, 8.0))
    }

    @Test fun highwayOffRouteReroutesOnFirstConfirmedFix() {
        val decision = OffRouteDecision(candidate = true, severe = false, thresholdMeters = 40.0)
        assertEquals(1, offRouteConfirmationsRequired(decision, 20.0))
    }

    @Test fun lowSpeedMarginalOffRouteNeedsSecondConfirmation() {
        val decision = OffRouteDecision(candidate = true, severe = false, thresholdMeters = 30.0)
        assertEquals(2, offRouteConfirmationsRequired(decision, 5.0))
    }

    @Test fun fusedSpeedIsConvertedDirectlyToHudKmh() {
        assertEquals(90.0, displaySpeedKmh(25.0), 0.001)
    }

    @Test fun headingUpCameraUsesVehicleBearing() {
        assertEquals(123.0, cameraBearingForMode(MapViewMode.HEADING_UP, 123f), 0.001)
        assertEquals(0.0, cameraBearingForMode(MapViewMode.NORTH_UP, 123f), 0.001)
    }

    @Test fun lookAheadGrowsWithDrivingSpeed() {
        assertTrue(lookAheadMetersForSpeed(100.0) > lookAheadMetersForSpeed(30.0))
    }

    @Test fun geoInterpolationProducesTrueMidpointInsteadOfJump() {
        val a = LatLng(35.7000, 51.4000)
        val b = LatLng(35.7020, 51.4040)
        val mid = interpolateGeoPoint(a, b, 0.5f)
        assertEquals(35.7010, mid.latitude, 0.000001)
        assertEquals(51.4020, mid.longitude, 0.000001)
    }

    @Test fun englishTurnInstructionBecomesNaturalPersian() {
        assertEquals("به چپ بپیچید", naturalPersianManeuver("Turn left"))
        assertEquals("مستقیم ادامه دهید", naturalPersianManeuver("Continue straight"))
    }

    @Test fun etaUsesRemainingRouteFraction() {
        assertEquals(20, estimateRemainingMinutes(40, 20.0, 10.0))
    }
}
""")

engine = root / "app/src/main/java/ir/rahyar/app/core/navigation/NavigationEngine.kt"
e = engine.read_text()
e = e.replace(
    "        val fractionRemaining = if (route.distanceKm > 0.0) (remainingKm / route.distanceKm).coerceIn(0.0, 1.0) else 1.0\n        val remainingMinutes = max(1, (route.durationMinutes * fractionRemaining).toInt())",
    "        val remainingMinutes = estimateRemainingMinutes(route.durationMinutes, route.distanceKm, remainingKm)",
    1
)
old_turn = """        val nextTurn = maneuver?.instruction
            ?: route.steps.firstOrNull()?.instruction
            ?: "ادامه مسیر"
"""
new_turn = """        val nextTurn = naturalPersianManeuver(
            maneuver?.instruction
                ?: route.steps.firstOrNull()?.instruction
                ?: "ادامه مسیر"
        )
"""
if old_turn not in e:
    raise SystemExit("Run49 nextTurn target missing")
e = e.replace(old_turn, new_turn, 1)
e = e.replace(
    "            speedKmh = signal.speedMps * 3.6,",
    "            speedKmh = displaySpeedKmh(signal.speedMps),",
    1
)
e = e.replace(
    "        val confirmationsRequired = if (decision.severe || speedMps >= 15.0) 1 else 2",
    "        val confirmationsRequired = offRouteConfirmationsRequired(decision, speedMps)",
    1
)
engine.write_text(e)

active = root / "app/src/main/java/ir/rahyar/app/ui/screens/ActiveNavigationScreen.kt"
a = active.read_text()
if "import ir.rahyar.app.core.navigation.cameraBearingForMode" not in a:
    anchor = "import ir.rahyar.app.core.navigation.forwardPoint\n"
    if anchor not in a:
        raise SystemExit("Run49 camera import anchor missing")
    a = a.replace(
        anchor,
        anchor + "import ir.rahyar.app.core.navigation.cameraBearingForMode\nimport ir.rahyar.app.core.navigation.lookAheadMetersForSpeed\n",
        1
    )
a = a.replace(
    """        val speedMps = current.speedKmh / 3.6
        val lookAheadMeters = (32.0 + speedMps * 4.2).coerceIn(32.0, 115.0)""",
    """        val lookAheadMeters = lookAheadMetersForSpeed(current.speedKmh)""",
    1
)
a = a.replace(
    """        val cameraBearing = when (quickSettings.mapViewMode) {
            MapViewMode.NORTH_UP -> 0.0
            MapViewMode.HEADING_UP, MapViewMode.THREE_D -> current.bearing.toDouble()
        }""",
    """        val cameraBearing = cameraBearingForMode(quickSettings.mapViewMode, current.bearing)""",
    1
)
active.write_text(a)
