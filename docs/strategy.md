# Trading Strategy (BUY Only)

Dokumen ini menjelaskan aturan teknikal untuk menghasilkan sinyal BUY
pada sistem Analisa Saham Indonesia.

## 1. Prinsip Dasar
- Sistem hanya membuka posisi BUY.
- EXIT dilakukan menggunakan TP/SL (dari Signal Storage).
- Sinyal tidak ditimpa kecuali status sudah TP atau SL.

## 2. Indikator yang digunakan
- EMA 9
- EMA 21
- SMA 50 (trend filter)
- ATR 14 (volatility, menentukan TP/SL)
- (opsional) RSI untuk filter momentum

## 3. Aturan Entry (Buy)
Sinyal BUY terjadi jika memenuhi semua kondisi:

1. **EMA 9 cross up EMA 21**
   - `EMA_9[t] > EMA_21[t]`
   - `EMA_9[t-1] <= EMA_21[t-1]`

2. **Harga mengikuti trend (trend filter)**
   - `Close[t] > SMA_50[t]`

3. **Volatilitas valid**
   - `ATR_14[t] > 0`

4. **(Opsional) Momentum positif**
   - `RSI[t] > 50`

## 4. Penentu TP/SL
- Entry = `Close[t]`
- TP = `Entry + 2 * ATR_14[t]`
- SL = `Entry - 1.5 * ATR_14[t]`

## 5. Output
Strategy menghasilkan dictionary:

{
"timestamp": ...,
"signal": "BUY",
"entry": ...,
"tp": ...,
"sl": ...,
"reason": "...",
}


## 6. Unit Test
- Berikan contoh dataset sintetis yang mengandung cross EMA.
- Pastikan sinyal BUY muncul pada bar yang sesuai.

