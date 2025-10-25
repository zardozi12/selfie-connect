import qrcode
import os

def generate_qr_for_link(link: str, qr_path: str) -> str:
    """
    Generate QR code for a share/public link and save to file
    """
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )
    qr.add_data(link)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    os.makedirs(os.path.dirname(qr_path), exist_ok=True)
    img.save(qr_path)
    return qr_path
