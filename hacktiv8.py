import os
import datetime
import time
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from google import genai
from dotenv import load_dotenv

import json

# Muat variabel environment
load_dotenv()

# ============================================================
# KONFIGURASI APLIKASI
# ============================================================

st.set_page_config(
    page_title="SahamAI - AI Stock Analyst",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.8-flash"
HISTORY_FILE = "chat_history.json"

if not GEMINI_API_KEY:
    st.error("⚠️ GEMINI_API_KEY belum diset di file .env. Mohon periksa kembali!")
    st.stop()

# Inisialisasi client Gemini
client = genai.Client(api_key=GEMINI_API_KEY)


# ============================================================
# PENYIMPANAN RIWAYAT CHAT (PERSISTENT & SANGAT RINGAN)
# ============================================================

def simpan_riwayat(messages, ticker):
    """Menyimpan pesan chat dan ticker aktif ke file JSON ringan."""
    try:
        data = {
            "ticker": ticker,
            "messages": messages[-40:] # Batasi 40 pesan terakhir
        }
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def muat_riwayat():
    """Memuat riwayat chat dari sesi sebelumnya jika tersedia."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


# ============================================================
# STATE MANAGEMENT
# ============================================================

saved_data = muat_riwayat()

if "messages" not in st.session_state:
    st.session_state.messages = saved_data.get("messages", []) if saved_data else []

if "latest_analysis" not in st.session_state:
    st.session_state.latest_analysis = None

if "current_ticker" not in st.session_state:
    st.session_state.current_ticker = saved_data.get("ticker", "BBCA.JK") if saved_data else "BBCA.JK"


# ============================================================
# HELPER: PANGGIL GEMINI DENGAN RETRY 503
# ============================================================

def panggil_gemini_aman(contents, config=None):
    """Panggil Gemini dengan retry otomatis saat terjadi 503/overloaded."""
    max_retries = 3
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config
            )
            if response and response.text:
                return response.text.strip(), GEMINI_MODEL
        except Exception as e:
            last_err = e
            err_str = str(e)
            is_overloaded = (
                "503" in err_str
                or "UNAVAILABLE" in err_str
                or "overloaded" in err_str.lower()
                or "429" in err_str
            )
            if is_overloaded and attempt < max_retries:
                time.sleep(2 * attempt)
            else:
                raise e

    raise last_err if last_err else RuntimeError("Model Gemini tidak merespons.")


# ============================================================
# FUNGSI PENGAMBILAN DATA SAHAM
# ============================================================

@st.cache_data(ttl=60)
def ambil_data_saham(ticker_symbol):
    ticker_symbol = ticker_symbol.upper().strip()
    ticker = yf.Ticker(ticker_symbol)

    # Data harian untuk Close Kemarin & SMA20
    daily_data = ticker.history(period="1mo", interval="1d").dropna()
    if daily_data.empty or len(daily_data) < 2:
        return None, "Data harian tidak cukup atau ticker tidak ditemukan."

    # Data per jam untuk intraday
    hourly_data = ticker.history(period="5d", interval="1h").dropna()

    # Harga saat ini
    if not hourly_data.empty:
        latest_candle = hourly_data.iloc[-1]
        latest_time_idx = hourly_data.index[-1]
    else:
        latest_candle = daily_data.iloc[-1]
        latest_time_idx = daily_data.index[-1]

    current_price = float(latest_candle["Close"])
    current_open = float(latest_candle["Open"])
    current_high = float(latest_candle["High"])
    current_low = float(latest_candle["Low"])
    hourly_volume = int(latest_candle["Volume"])

    # Penutupan kemarin
    previous_daily_close = float(daily_data["Close"].iloc[-2])
    price_change = current_price - previous_daily_close
    price_change_percent = (price_change / previous_daily_close) * 100

    today_total_volume = int(daily_data["Volume"].iloc[-1])

    # SMA 20
    if len(daily_data) >= 20:
        daily_data["SMA20"] = daily_data["Close"].rolling(20).mean()
        sma20 = float(daily_data["SMA20"].iloc[-1])
    else:
        sma20 = None

    # Volume perbandingan
    avg_daily_volume = float(daily_data["Volume"].tail(20).mean())
    vol_vs_avg_ratio = (today_total_volume / avg_daily_volume) if avg_daily_volume > 0 else 1.0

    # Timestamp dalam WIB
    if hasattr(latest_time_idx, 'tzinfo') and latest_time_idx.tzinfo is not None:
        candle_time = latest_time_idx.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
    else:
        candle_time = latest_time_idx
    candle_time_str = candle_time.strftime("%Y-%m-%d %H:%M:%S WIB")

    return {
        "ticker": ticker_symbol,
        "daily_data": daily_data,
        "hourly_data": hourly_data,
        "current_price": current_price,
        "current_open": current_open,
        "current_high": current_high,
        "current_low": current_low,
        "hourly_volume": hourly_volume,
        "previous_daily_close": previous_daily_close,
        "price_change": price_change,
        "price_change_percent": price_change_percent,
        "today_total_volume": today_total_volume,
        "sma20": sma20,
        "vol_vs_avg_ratio": vol_vs_avg_ratio,
        "candle_time_str": candle_time_str
    }, None


# ============================================================
# FUNGSI ANALISIS AI
# ============================================================

def buat_analisis_ai(stock_info):
    now_str = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=7))
    ).strftime("%Y-%m-%d %H:%M:%S WIB")

    market_data = f"""
Ticker: {stock_info['ticker']}

📅 Waktu Candle Terakhir: {stock_info['candle_time_str']}
🕐 Waktu Analisis: {now_str}

Harga Saat Ini: {stock_info['current_price']:,.2f}
Penutupan Kemarin (Previous Close): {stock_info['previous_daily_close']:,.2f}

Perubahan Harga Hari Ini:
{stock_info['price_change']:+,.2f} ({stock_info['price_change_percent']:+.2f}%)

Candle 1 Jam Terakhir:
Open: {stock_info['current_open']:,.2f} | High: {stock_info['current_high']:,.2f} | Low: {stock_info['current_low']:,.2f} | Close: {stock_info['current_price']:,.2f}
Volume 1 Jam Terakhir: {stock_info['hourly_volume']:,} lembar saham

Total Volume Perdagangan Hari Ini:
{stock_info['today_total_volume']:,} lembar saham (Rasio terhadap rata-rata 20 hari: {stock_info['vol_vs_avg_ratio']:.2f}x)
"""

    if stock_info['sma20'] is not None:
        status_sma = "DI ATAS" if stock_info['current_price'] >= stock_info['sma20'] else "DI BAWAH"
        market_data += f"""
SMA 20 Hari (Indikator Tren Harian):
{stock_info['sma20']:,.2f} (Harga saat ini {status_sma} SMA 20)
"""

    prompt = f"""
Anda adalah analis pasar saham yang ramah dan to-the-point.
Gunakan bahasa Indonesia yang sederhana, jelas, dan mudah dipahami orang awam (jangan gunakan istilah teknis yang berbelit-belit).

Analisis data pasar berikut secara objektif:

ATURAN PENTING:
- Gunakan data yang diberikan saja, jangan mengarang.
- Buat penjelasan ringkas dan padat.

DATA PASAR:
{market_data}

Berikan respons dalam struktur markdown persis seperti ini:

### 📈 ARAH TREN
(Jelaskan arah pergerakan harga saat ini dengan bahasa sederhana: apakah sedang naik, turun, atau datar/santai)

### 📊 VOLUME TRANSAKSI
(Jelaskan keaktifan transaksi berdasarkan data volume harian dan candle 1 jam: apakah tergolong ramai di atas rata-rata, biasa saja, atau sepi)

### 💡 REKOMENDASI AI
Pilih SATU: **🟢 BUY** atau **🟡 WAIT (TUNGGU DULU)** atau **🔴 SELL**

(Jelaskan alasannya secara singkat dalam 1-2 kalimat mudah dipahami)

**Jika BUY:**
- 🎯 Area beli yang bagus: [Sebutkan rentang harga]
- 🚀 Target harga jual: [Sebutkan target harga]
- 🛑 Batas cut loss: [Sebutkan batas harga jika turun]

**Jika WAIT:**
- ⏳ Kenapa harus tunggu: [Jelaskan singkat]
- 🛒 **Kapan & di harga berapa boleh BUY:** [Jelaskan secara jelas di harga berapa atau momen apa yang aman untuk mulai beli, contoh: 'Beli jika harga bertahan di atas Rp... atau mulai memantul dari Rp...']
- 🎯 Target harga jika nanti masuk: [Sebutkan target]
- 🛑 Batas cut loss jika nanti masuk: [Sebutkan batas harga]

**Jika SELL:**
- ⚠️ Alasan jual / hindari: [Jelaskan singkat bahayanya]

### ⚠️ CATATAN RISIKO
(Beri 1-2 risiko utama secara sederhana)
"""

    config = {"thinking_config": {"thinking_budget": 0}}
    hasil, model_terpakai = panggil_gemini_aman(prompt, config=config)
    return hasil, model_terpakai


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("⚙️ Pengaturan SahamAI")
    st.markdown("Platform Analisis Saham Berbasis Kecerdasan Buatan Google Gemini.")

    st.divider()

    st.subheader("🔍 Pilih Ticker Saham")
    input_ticker = st.text_input(
        "Masukkan Simbol Ticker:",
        value=st.session_state.current_ticker,
        help="Gunakan akhiran .JK untuk saham Indonesia (contoh: BBCA.JK, BBRI.JK). Simbol AS tanpa akhiran (contoh: AAPL, NVDA)."
    )

    st.caption("Pilihan Populer:")
    cols_btn = st.columns(3)
    if cols_btn[0].button("BBCA.JK"):
        input_ticker = "BBCA.JK"
    if cols_btn[1].button("BBRI.JK"):
        input_ticker = "BBRI.JK"
    if cols_btn[2].button("TLKM.JK"):
        input_ticker = "TLKM.JK"

    cols_btn2 = st.columns(3)
    if cols_btn2[0].button("ASII.JK"):
        input_ticker = "ASII.JK"
    if cols_btn2[1].button("AAPL"):
        input_ticker = "AAPL"
    if cols_btn2[2].button("NVDA"):
        input_ticker = "NVDA"

    st.divider()

    tombol_analisis = st.button("🚀 Analisis Saham Sekarang", type="primary", width="stretch")

    st.divider()
    if st.button("🗑️ Bersihkan Riwayat Chat", width="stretch"):
        st.session_state.messages = []
        if os.path.exists(HISTORY_FILE):
            try:
                os.remove(HISTORY_FILE)
            except Exception:
                pass
        st.rerun()

    st.caption("💡 Model yang digunakan: Gemini 3.8 Flash")


# ============================================================
# HEADER & DASHBOARD UTAMA
# ============================================================

st.title("📈 SahamAI - Dashboard & AI Chat")
st.write("Analisis teknikal cerdas, harga pasar terkini, dan konsultasi interaktif tanpa perlu Telegram.")

# Trigger analisis HANYA jika tombol diklik oleh pengguna (tidak otomatis saat awal buka)
if tombol_analisis:
    st.session_state.current_ticker = input_ticker.upper().strip()
    
    with st.spinner(f"🔄 Mengambil data pasar untuk {st.session_state.current_ticker}..."):
        data_saham, err = ambil_data_saham(st.session_state.current_ticker)

    if err:
        st.error(f"❌ {err}")
    else:
        hasil_ai = None
        model_used = GEMINI_MODEL
        try:
            with st.spinner(f"🤖 Menjalankan analisis AI Gemini untuk {st.session_state.current_ticker}..."):
                hasil_ai, model_used = buat_analisis_ai(data_saham)
        except Exception as e:
            st.warning(f"⚠️ Analisis AI gagal dimuat sementara (server Gemini sibuk): {e}. Menampilkan data pasar.")
            hasil_ai = f"⚠️ Analisis AI sedang mengalami kendala sementara ({e}). Silakan klik tombol 'Analisis Saham Sekarang' untuk mencoba lagi."

        st.session_state.latest_analysis = {
            "data": data_saham,
            "ai_text": hasil_ai,
            "model_used": model_used
        }

        # Simpan ke riwayat percakapan agar chatbot ingat
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"📊 **Hasil Analisis untuk {data_saham['ticker']}**:\n\n{hasil_ai}"
        })
        simpan_riwayat(st.session_state.messages, st.session_state.current_ticker)

# ============================================================
# TAMPILAN DASHBOARD (METRICS & GRAFIK)
# ============================================================

if st.session_state.latest_analysis:
    analysis = st.session_state.latest_analysis
    d = analysis["data"]

    # 1. Baris Metric Ringkasan
    st.subheader(f"📊 Ringkasan Pasar: {d['ticker']}")
    col1, col2, col3, col4 = st.columns(4)

    warna_delta = "normal" if d['price_change'] >= 0 else "inverse"
    col1.metric(
        label="Harga Saat Ini",
        value=f"Rp {d['current_price']:,.2f}" if ".JK" in d['ticker'] else f"${d['current_price']:,.2f}",
        delta=f"{d['price_change']:+,.2f} ({d['price_change_percent']:+.2f}%)"
    )

    col2.metric(
        label="Penutupan Kemarin (Prev Close)",
        value=f"Rp {d['previous_daily_close']:,.2f}" if ".JK" in d['ticker'] else f"${d['previous_daily_close']:,.2f}"
    )

    col3.metric(
        label="Total Volume Hari Ini",
        value=f"{d['today_total_volume']:,} lbr",
        delta=f"{d['vol_vs_avg_ratio']:.2f}x vs Rata-rata 20 Hari"
    )

    if d['sma20'] is not None:
        status_sma = "Di Atas SMA20 🟢" if d['current_price'] >= d['sma20'] else "Di Bawah SMA20 🔴"
        col4.metric(
            label="SMA 20 Hari",
            value=f"{d['sma20']:,.2f}",
            delta=status_sma
        )

    st.caption(f"📅 Data per: {d['candle_time_str']} | Model AI: {analysis['model_used']}")

    # 2. Grafik Candlestick Interaktif
    st.subheader("📉 Grafik Pergerakan Harga (Intraday)")
    chart_data = d["hourly_data"] if not d["hourly_data"].empty else d["daily_data"]
    
    fig = go.Figure(data=[go.Candlestick(
        x=chart_data.index,
        open=chart_data['Open'],
        high=chart_data['High'],
        low=chart_data['Low'],
        close=chart_data['Close'],
        name="Candle"
    )])
    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=400,
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig, width="stretch")

    # 3. Kotak Rekomendasi AI
    st.subheader(f"💡 Hasil Analisis AI ({d['ticker']})")
    with st.container(border=True):
        st.markdown(analysis["ai_text"])


# ============================================================
# CHATBOT INTERAKTIF (SEPERTI CHATGPT)
# ============================================================

st.divider()
st.subheader("💬 Tanya Jawab dengan AI (Chat Assistant)")
st.caption("Anda dapat menanyakan hal lanjutan seputar saham di atas (misal: 'Kapan saat tepat untuk buy?', 'Kenapa volume-nya sepi?', dll).")

# Tampilkan seluruh riwayat pesan
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input pesan dari user
user_prompt = st.chat_input("Ketik pertanyaan Anda di sini...")

if user_prompt:
    # 1. Tampilkan pesan user
    st.chat_message("user").markdown(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # 2. Bangun history untuk Gemini
    history_gemini = []
    for m in st.session_state.messages:
        role = "user" if m["role"] == "user" else "model"
        history_gemini.append({
            "role": role,
            "parts": [{"text": m["content"]}]
        })

    now_time = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=7))
    ).strftime("%A, %d %B %Y %H:%M:%S WIB")

    system_instruction = (
        f"Anda adalah asisten analisis pasar saham yang cerdas, ramah, dan cepat. "
        f"Waktu saat ini adalah {now_time}. "
        f"Gunakan bahasa Indonesia yang jelas, ringkas, dan mudah dipahami orang awam. "
        f"Anda memiliki akses penuh ke riwayat percakapan dan data saham yang baru saja dianalisis di atas. "
        f"Jawab pertanyaan pengguna secara akurat dan to-the-point."
    )

    with st.chat_message("assistant"):
        with st.spinner("⏳ Sedang berpikir..."):
            try:
                config_chat = {
                    "system_instruction": system_instruction,
                    "thinking_config": {"thinking_budget": 0}
                }
                reply_text, model_used = panggil_gemini_aman(history_gemini, config=config_chat)
                st.markdown(reply_text)
                st.session_state.messages.append({"role": "assistant", "content": reply_text})
            except Exception as e:
                err_msg = f"⚠️ Maaf, terjadi kesalahan saat menghubungi AI: {e}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})

    # Simpan percakapan ke file JSON lokal agar tersambung di sesi berikutnya
    simpan_riwayat(st.session_state.messages, st.session_state.current_ticker)
