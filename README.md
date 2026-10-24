# Wireless File Share App

A Python Flask application for sharing files wirelessly between a laptop and a mobile device using QR codes and a local Wi-Fi network.

## Features

- QR-code-based mobile access
- Laptop-to-mobile file sharing
- Mobile-to-laptop file uploads
- Local network file transfer
- Built with Python and Flask

## Tech Stack

- Python
- Flask
- QR code generation

## Project Structure

```text
wireless-file-share-app/
├── app.py
├── server.py
├── handler.py
├── browser_launcher.py
├── qr_generator.py
├── requirements.txt
└── utils.py
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Ayanshaikh-1209/wireless-file-share-app.git
cd wireless-file-share-app
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Run the application

```powershell
python app.py
```

Follow the terminal instructions to access the application. For mobile access, connect both devices to the same trusted Wi-Fi network.

## Security

- Use the application on a trusted local network.
- Do not expose the development server directly to the public internet.
- Share only files you intend to transfer.

## Author

**Ayan Shaikh**

GitHub: [Ayanshaikh-1209](https://github.com/Ayanshaikh-1209)

## Future Improvements

- Responsive user interface
- File transfer progress indicator
- Improved error handling
- Additional file validation and security

