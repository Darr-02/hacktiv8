# 📈 SahamAI - AI-Powered Stock Analyst & Interactive Chatbot

**SahamAI** adalah platform analisis teknikal saham cerdas yang mengintegrasikan data pasar saham publik (**Yahoo Finance**) dengan kemampuan penalaran **Google Gemini AI**. Proyek ini hadir dalam bentuk **Web Dashboard Streamlit** (`hacktiv8.py`).

---

## 🌟 Fitur Utama

- 📊 **Metrik Pasar Real-time & Akurat**:
  - Harga terkini dan penutupan kemarin (*Previous Close*).
  - Perubahan harga resmi harian (Rp & %) sesuai standar bursa (IDX/RTI/Stockbit).
  - Akumulasi total volume perdagangan harian dan perbandingannya terhadap rata-rata 20 hari.
  - Posisi harga terhadap indikator **SMA 20 Hari**.
- 📉 **Grafik Candlestick Interaktif**:
  - Visualisasi pergerakan harga per jam (*1-Hour Intraday Candles*) menggunakan Plotly yang dapat di-*zoom*, digeser, dan diteliti.
- 💡 **Rekomendasi AI yang Ramah Pemula**:
  - Evaluasi arah tren dan volume dalam bahasa yang sederhana dan lugas tanpa istilah rumit.
  - Rekomendasi jelas: **🟢 BUY**, **🟡 WAIT (TUNGGU DULU)**, atau **🔴 SELL**.
  - **Panduan Level Beli Spesifik saat WAIT**: Tetap mencantumkan di harga berapa atau kondisi apa yang aman untuk mulai masuk, target harga, dan batas proteksi (*cut loss*).
- 💬 **AI Chat Assistant Interaktif (Multi-Turn Chat)**:
  - Berfungsi seperti ChatGPT / Gemini langsung di ruang obrolan.
  - **Mengingat Konteks Sesi**: Mampu menjawab pertanyaan lanjutan seputar saham yang baru saja dicek (misal: *"Kapan waktu terbaik untuk buy BBCA tadi?"*).
  - **Penyimpanan Riwayat Otomatis**: Chat tidak hilang saat browser ditutup, langsung tersambung kembali saat aplikasi dibuka kembali.
- 🛡️ **Anti-Overload & Robust Networking**:
  - Dilengkapi mekanisme auto-retry jika server AI sedang padat (`503 UNAVAILABLE`).
  - Menggunakan HTTP Persistent Connection (*Keep-Alive*) untuk koneksi yang stabil dan cepat.

---

## 📁 Struktur Direktori

```text
hacktiv8/
├── hacktiv8.py         # Versi Web App interaktif (Streamlit)
├── requirements.txt    # Daftar pustaka / dependencies Python
├── .gitignore          # Pengaman file rahasia agar tidak ter-upload ke Git
├── .env.example        # Template konfigurasi environment
└── README.md           # Dokumentasi proyek
```

---

## 🚀 Panduan Instalasi & Penggunaan

### 1. Kloning / Buka Folder Proyek
Pastikan terminal berada di direktori proyek:
```bash
cd hacktiv8
```

### 2. Pasang Dependencies
Pastikan Python 3.10+ sudah terpasang, lalu pasang library yang dibutuhkan cukup dengan perintah:
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Environment (`.env`)
Salin file `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```
Buka file `.env` dan masukkan API Key Google Gemini Anda:
```env
GEMINI_API_KEY=...your_gemini_api_key_here...
```
---

## 🖥️ Menjalankan Aplikasi

### Web App Streamlit (`hacktiv8.py`)
Buka langsung di browser lokal Anda:

```bash
streamlit run hacktiv8.py
```
atau menggunakan modul Python:
```bash
py -m streamlit run hacktiv8.py
```

Aplikasi akan otomatis terbuka di browser pada alamat:
👉 **`http://localhost:8501`**

#### Cara Penggunaan Web:
1. Masukkan simbol ticker di sidebar (contoh: `BBCA.JK`, `BBRI.JK`, `TLKM.JK` untuk saham Indonesia, atau `AAPL`, `NVDA` untuk saham AS).
2. Klik tombol **"🚀 Analisis Saham Sekarang"**.
3. Gulir ke bawah untuk melihat grafik candlestick dan rekomendasi AI.
4. Gunakan kolom **Tanya Jawab AI** di bagian bawah untuk konsultasi lanjutan.

---


```bash
py botsaham.py
```

#### Perintah di Telegram:
- `/start` : Menampilkan pesan sambutan dan panduan perintah.
- `/cek BBCA.JK` : Menjalankan analisis teknikal saham lengkap dengan timestamp data.
- **Chat Bebas**: Ketik pertanyaan apa saja (misal: *"Kapan waktu tepat untuk buy?"*), AI akan langsung menjawab percakapan Anda secara alami.

---

## 🔒 Privasi & Keamanan Data
- Seluruh API Key dan kredensial rahasia disimpan di file `.env` lokal dan tidak pernah di-*hardcode* di dalam script.
- Jangan pernah mengunggah file `.env` ke repositori publik (GitHub/GitLab). Pastikan file `.env` tercantum di dalam `.gitignore`.

---

## 📄 Lisensi
Proyek ini dibuat untuk keperluan edukasi dan analisis pasar finansial pribadi. Data yang disajikan bersumber dari Yahoo Finance dan analisis AI bersifat opini analitis, bukan jaminan nasihat keuangan mutlak (*Disclaimer: Do Your Own Research*).
