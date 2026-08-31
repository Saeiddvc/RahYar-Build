from pathlib import Path

root = Path(".")
font_file = root / "app/src/main/java/ir/rahyar/app/ui/theme/Font.kt"
font_file.write_text("""package ir.rahyar.app.ui.theme

import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import ir.rahyar.app.R

val IranSansFaNum = FontFamily(
    Font(R.font.iransans_fanum_regular, FontWeight.Normal),
    Font(R.font.iransans_fanum_medium, FontWeight.Medium),
    Font(R.font.iransans_fanum_bold, FontWeight.Bold)
)
""")

typography = root / "app/src/main/java/ir/rahyar/app/ui/theme/Typography.kt"
typography.write_text("""package ir.rahyar.app.ui.theme

import androidx.compose.material3.Typography

private val BaseTypography = Typography()

val RahyarTypography = Typography(
    displayLarge = BaseTypography.displayLarge.copy(fontFamily = IranSansFaNum),
    displayMedium = BaseTypography.displayMedium.copy(fontFamily = IranSansFaNum),
    displaySmall = BaseTypography.displaySmall.copy(fontFamily = IranSansFaNum),
    headlineLarge = BaseTypography.headlineLarge.copy(fontFamily = IranSansFaNum),
    headlineMedium = BaseTypography.headlineMedium.copy(fontFamily = IranSansFaNum),
    headlineSmall = BaseTypography.headlineSmall.copy(fontFamily = IranSansFaNum),
    titleLarge = BaseTypography.titleLarge.copy(fontFamily = IranSansFaNum),
    titleMedium = BaseTypography.titleMedium.copy(fontFamily = IranSansFaNum),
    titleSmall = BaseTypography.titleSmall.copy(fontFamily = IranSansFaNum),
    bodyLarge = BaseTypography.bodyLarge.copy(fontFamily = IranSansFaNum),
    bodyMedium = BaseTypography.bodyMedium.copy(fontFamily = IranSansFaNum),
    bodySmall = BaseTypography.bodySmall.copy(fontFamily = IranSansFaNum),
    labelLarge = BaseTypography.labelLarge.copy(fontFamily = IranSansFaNum),
    labelMedium = BaseTypography.labelMedium.copy(fontFamily = IranSansFaNum),
    labelSmall = BaseTypography.labelSmall.copy(fontFamily = IranSansFaNum)
)
""")

quick_test = root / "app/src/test/java/ir/rahyar/app/navigation/QuickSettingsContractTest.kt"
quick_test.parent.mkdir(parents=True, exist_ok=True)
quick_test.write_text("""package ir.rahyar.app.navigation

import ir.rahyar.app.domain.models.MapViewMode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class QuickSettingsContractTest {
    @Test
    fun quickSettingsContainAllRequiredControlsAndPersistInSession() {
        val session = NavigationSession()
        session.updateQuickSettings {
            it.copy(
                voiceGuidanceEnabled = false,
                voiceAlertsEnabled = false,
                mapViewMode = MapViewMode.THREE_D,
                showTraffic = true,
                avoidTrafficZone = true,
                avoidPollutionZone = true,
                avoidTollRoads = true,
                rerouteOnHeavyTraffic = true,
                rerouteOnSevereWeather = true,
                speedLimitAlertsEnabled = true
            )
        }
        val q = session.state.value.quickSettings
        assertFalse(q.voiceGuidanceEnabled)
        assertFalse(q.voiceAlertsEnabled)
        assertEquals(MapViewMode.THREE_D, q.mapViewMode)
        assertTrue(q.showTraffic)
        assertTrue(q.avoidTrafficZone)
        assertTrue(q.avoidPollutionZone)
        assertTrue(q.avoidTollRoads)
        assertTrue(q.rerouteOnHeavyTraffic)
        assertTrue(q.rerouteOnSevereWeather)
        assertTrue(q.speedLimitAlertsEnabled)
    }
}
""")

font_family_xml = root / "app/src/main/res/font/iransans.xml"
font_family_xml.parent.mkdir(parents=True, exist_ok=True)
font_family_xml.write_text("""<?xml version="1.0" encoding="utf-8"?>
<font-family xmlns:app="http://schemas.android.com/apk/res-auto">
    <font
        app:font="@font/iransans_fanum_regular"
        app:fontStyle="normal"
        app:fontWeight="400" />
    <font
        app:font="@font/iransans_fanum_medium"
        app:fontStyle="normal"
        app:fontWeight="500" />
    <font
        app:font="@font/iransans_fanum_bold"
        app:fontStyle="normal"
        app:fontWeight="700" />
</font-family>
""")
