from pathlib import Path

root = Path(".")

glyph = root / "app/src/main/java/ir/rahyar/app/core/navigation/VehicleGlyphSpec.kt"
glyph.write_text("""package ir.rahyar.app.core.navigation

data class VehicleGlyphPoint(val x: Float, val y: Float)

data class VehicleGlyphRect(
    val left: Float,
    val top: Float,
    val right: Float,
    val bottom: Float
)

data class NavigationVehicleGlyphSpec(
    val width: Int,
    val height: Int,
    val body: List<VehicleGlyphPoint>,
    val windshield: VehicleGlyphRect,
    val lamps: List<VehicleGlyphPoint>
)

fun navigationVehicleGlyphSpec(): NavigationVehicleGlyphSpec =
    NavigationVehicleGlyphSpec(
        width = 72,
        height = 96,
        body = listOf(
            VehicleGlyphPoint(36f, 3f),
            VehicleGlyphPoint(63f, 28f),
            VehicleGlyphPoint(60f, 80f),
            VehicleGlyphPoint(48f, 91f),
            VehicleGlyphPoint(24f, 91f),
            VehicleGlyphPoint(12f, 80f),
            VehicleGlyphPoint(9f, 28f)
        ),
        windshield = VehicleGlyphRect(
            left = 22f,
            top = 34f,
            right = 50f,
            bottom = 55f
        ),
        lamps = listOf(
            VehicleGlyphPoint(22f, 71f),
            VehicleGlyphPoint(50f, 71f)
        )
    )
""")

test = root / "app/src/test/java/ir/rahyar/app/core/navigation/VehicleGlyphSpecTest.kt"
test.parent.mkdir(parents=True, exist_ok=True)
test.write_text("""package ir.rahyar.app.core.navigation

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

class VehicleGlyphSpecTest {
    @Test
    fun liveMarkerGlyphIsUnambiguouslyCarShapedNotPinShaped() {
        val spec = navigationVehicleGlyphSpec()

        assertEquals(72, spec.width)
        assertEquals(96, spec.height)
        assertTrue(spec.body.size >= 7)
        assertTrue(spec.windshield.right > spec.windshield.left)
        assertTrue(spec.windshield.bottom > spec.windshield.top)
        assertEquals(2, spec.lamps.size)

        val top = spec.body.minByOrNull { it.y }!!
        assertTrue(abs(top.x - spec.width / 2f) <= 1f)

        val bottom = spec.body.filter { it.y >= 90f }
        assertTrue(bottom.size >= 2)
        val bottomWidth = bottom.maxOf { it.x } - bottom.minOf { it.x }
        assertTrue(bottomWidth >= 20f)

        val lampMidpoint = (spec.lamps[0].x + spec.lamps[1].x) / 2f
        assertTrue(abs(lampMidpoint - spec.width / 2f) <= 1f)
        assertTrue(spec.lamps[0].x != spec.lamps[1].x)
    }
}
""")

active = root / "app/src/main/java/ir/rahyar/app/ui/screens/ActiveNavigationScreen.kt"
a = active.read_text()
old = """private fun navigationVehicleBitmap(): Bitmap {
    val width = 72
    val height = 96
    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)

    val body = android.graphics.Path().apply {
        moveTo(width / 2f, 3f)
        lineTo(63f, 28f)
        lineTo(60f, 80f)
        lineTo(48f, 91f)
        lineTo(24f, 91f)
        lineTo(12f, 80f)
        lineTo(9f, 28f)
        close()
    }
"""
new = """private fun navigationVehicleBitmap(): Bitmap {
    val spec = ir.rahyar.app.core.navigation.navigationVehicleGlyphSpec()
    val width = spec.width
    val height = spec.height
    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)

    val body = android.graphics.Path().apply {
        val first = spec.body.first()
        moveTo(first.x, first.y)
        spec.body.drop(1).forEach { point ->
            lineTo(point.x, point.y)
        }
        close()
    }
"""
if old not in a:
    raise SystemExit("Run56 vehicle bitmap header target missing")
a = a.replace(old, new, 1)

old_windshield = """    canvas.drawRoundRect(22f, 34f, 50f, 55f, 7f, 7f, windshield)

    val lamp = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
        style = android.graphics.Paint.Style.FILL
        color = AndroidColor.WHITE
    }
    canvas.drawCircle(22f, 71f, 4f, lamp)
    canvas.drawCircle(50f, 71f, 4f, lamp)
"""
new_windshield = """    canvas.drawRoundRect(
        spec.windshield.left,
        spec.windshield.top,
        spec.windshield.right,
        spec.windshield.bottom,
        7f,
        7f,
        windshield
    )

    val lamp = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
        style = android.graphics.Paint.Style.FILL
        color = AndroidColor.WHITE
    }
    spec.lamps.forEach { point ->
        canvas.drawCircle(point.x, point.y, 4f, lamp)
    }
"""
if old_windshield not in a:
    raise SystemExit("Run56 vehicle windshield target missing")
a = a.replace(old_windshield, new_windshield, 1)
active.write_text(a)
