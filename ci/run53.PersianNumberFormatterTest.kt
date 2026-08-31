package ir.rahyar.app.core.format

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PersianNumberFormatterTest {
    @Test
    fun latinDigitsBecomePersianDigits() {
        assertEquals("۱۲۳۴۵۶۷۸۹۰", toPersianNumberText("1234567890"))
    }

    @Test
    fun arabicIndicDigitsNormalizeToPersianDigits() {
        assertEquals("۱۲۳۴۵۶۷۸۹۰", toPersianNumberText("١٢٣٤٥٦٧٨٩٠"))
    }

    @Test
    fun decimalSeparatorIsPersian() {
        val value = formatPersianDecimal(1913.1, 1)
        assertEquals("۱۹۱۳٫۱", value)
        assertFalse(value.contains('.'))
        assertTrue(value.contains('٫'))
    }
}
