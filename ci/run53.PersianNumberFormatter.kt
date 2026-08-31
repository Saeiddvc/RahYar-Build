package ir.rahyar.app.core.format

import java.util.Locale

fun toPersianNumberText(value: String): String =
    value
        .replace('0', '۰')
        .replace('1', '۱')
        .replace('2', '۲')
        .replace('3', '۳')
        .replace('4', '۴')
        .replace('5', '۵')
        .replace('6', '۶')
        .replace('7', '۷')
        .replace('8', '۸')
        .replace('9', '۹')
        .replace('٠', '۰')
        .replace('١', '۱')
        .replace('٢', '۲')
        .replace('٣', '۳')
        .replace('٤', '۴')
        .replace('٥', '۵')
        .replace('٦', '۶')
        .replace('٧', '۷')
        .replace('٨', '۸')
        .replace('٩', '۹')
        .replace('.', '٫')

fun formatPersianDecimal(
    value: Double,
    decimals: Int = 1
): String {
    val precision = decimals.coerceIn(0, 3)
    return toPersianNumberText(
        "%." + precision + "f"
    ).let { formatPattern ->
        toPersianNumberText(
            String.format(
                Locale.US,
                "%." + precision + "f",
                value
            )
        )
    }
}
