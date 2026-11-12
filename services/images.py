import base64
import io

from PIL import Image, ImageOps, UnidentifiedImageError

import config


class ImageInvalide(Exception):
    """Le fichier reçu n'est pas une image lisible."""


class ServiceImage:

    FORMATS_ACCEPTES = ["jpg", "jpeg", "png", "webp"]

    def __init__(self, cote_max: int | None = None, qualite: int | None = None):
        self.cote_max = cote_max or config.IMAGE_COTE_MAX
        self.qualite = qualite or config.IMAGE_QUALITE_JPEG

    def preparer(self, octets: bytes) -> bytes:
        
        try:
            image = Image.open(io.BytesIO(octets))
            image = ImageOps.exif_transpose(image)  
        except (UnidentifiedImageError, OSError) as erreur:
            raise ImageInvalide("Ce fichier n'est pas une image lisible.") from erreur

        image = image.convert("RGB")  
        image.thumbnail((self.cote_max, self.cote_max))  
        tampon = io.BytesIO()
        image.save(tampon, format="JPEG", quality=self.qualite)
        return tampon.getvalue()

    @staticmethod
    def vers_data_url(octets_jpeg: bytes) -> str:
        """Encode l'image en base64, au format attendu par l'API."""
        return "data:image/jpeg;base64," + base64.b64encode(octets_jpeg).decode("ascii")