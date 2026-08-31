package ir.rahyar.app.core.navigation

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.navigation.TracePoint
import ir.rahyar.app.navigation.TripTrace
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TripTraceQualityTest {
    @Test fun lowSpeedGpsJitterDoesNotBecomeRealTrip() {
        val jitter = TripTrace(
            (0..12).map { i ->
                TracePoint(
                    location = LatLng(
                        35.7000 + (if (i % 2 == 0) 0.000015 else -0.000015),
                        51.4000 + (if (i % 3 == 0) 0.000015 else -0.000010)
                    ),
                    timestampMillis = i * 5_000L,
                    speedKmh = 2.0,
                    heading = 0f,
                    accuracyMeters = 18f
                )
            }
        )
        assertFalse(isMeaningfulRealTrip(jitter))
    }

    @Test fun poorAccuracyFixIsRejectedFromTrace() {
        val point = TracePoint(
            LatLng(35.7, 51.4), 1_000L, 30.0, 0f, accuracyMeters = 95f
        )
        assertFalse(shouldAcceptTracePoint(null, point))
    }

    @Test fun impossibleTeleportJumpIsRejected() {
        val first = TracePoint(LatLng(35.7, 51.4), 1_000L, 20.0, 0f, 8f)
        val jump = TracePoint(LatLng(35.8, 51.5), 2_000L, 20.0, 0f, 8f)
        assertFalse(shouldAcceptTracePoint(first, jump))
    }

    @Test fun meaningfulMovementBuildsRealTrip() {
        val real = TripTrace(
            listOf(
                TracePoint(LatLng(35.7000, 51.4000), 0L, 28.0, 90f, 7f),
                TracePoint(LatLng(35.7000, 51.4010), 20_000L, 30.0, 90f, 7f),
                TracePoint(LatLng(35.7000, 51.4020), 40_000L, 32.0, 90f, 7f),
                TracePoint(LatLng(35.7000, 51.4030), 60_000L, 30.0, 90f, 7f)
            )
        )
        assertTrue(isMeaningfulRealTrip(real))
    }
}
