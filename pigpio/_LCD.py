#
import numpy as np
from PIL import Image
from PIL import ImageDraw


class _LCD:
    def __init__(self, pi, color_mode):
        self.pi         = pi
        self.color_mode = color_mode
        self.buffer     = Image.new(self.color_mode, self.size)

    def color565(self, r, g, b):
        """
        Convert red, green, blue components to a 16-bit 565 RGB value.
        Components should be values 0 to 255.
        """
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    def image_to_data(self, image):
        """
        Generator function to convert a PIL image to 16-bit 565 RGB bytes.
        """
        # NumPy is much faster at doing this. NumPy code provided by:
        # Keith (https://www.blogger.com/profile/02555547344016007163)
        pb = np.array(image.convert(self.color_mode)).astype('uint16')
        print('pb=%s' % pb[0])
        color = ((pb[:,:,0] & 0xF8) << 8) | ((pb[:,:,1] & 0xFC) << 3) | (pb[:,:,2] >> 3)
        return np.dstack(((color >> 8) & 0xFF, color & 0xFF)).flatten().tolist()

    def reset(self):
        pass

    def _init(self):
        pass

    def begin(self):
        self.reset()
        self._init()

    '''
    def display():
        pass
    '''

    def clear():
        pass

    def draw(self):
        return ImageDraw.Draw(self.buffer)
    
    def cleanup(self):
        print('%s.cleanup()' % __class__.__name__)
        self.clear()
