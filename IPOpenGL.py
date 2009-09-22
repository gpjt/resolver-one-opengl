import clr
clr.AddReference("System.Drawing")
clr.AddReference("System.Windows.Forms")
clr.AddReference("Tao.OpenGl")
clr.AddReference("Tao.Platform.Windows")

from System import *
from System.Threading import *
from System.ComponentModel import *
from System.Diagnostics import *
from System.Drawing import *
from System.Drawing.Imaging import *
from System.IO import *
from System.Runtime.InteropServices import *
from System.Windows.Forms import *
from Tao.OpenGl import *
from Tao.Platform.Windows import *

from os import path
import math

class SpinningBoxWindow(Form):

    def __init__(self, title, width, height):
        self.CreateParams.ClassStyle = self.CreateParams.ClassStyle | User.CS_HREDRAW | User.CS_VREDRAW | User.CS_OWNDC

        self.SetStyle(ControlStyles.AllPaintingInWmPaint, True)
        self.SetStyle(ControlStyles.DoubleBuffer, True)
        self.SetStyle(ControlStyles.Opaque, True)
        self.SetStyle(ControlStyles.ResizeRedraw, True)
        self.SetStyle(ControlStyles.UserPaint, True)

        self.FormBorderStyle = FormBorderStyle.Sizable

        self.Width = width
        self.Height = height
        self.Text = title

        self.active = True
        self.done = False

        self.Activated += self.Form_Activated
        self.Deactivate += self.Form_Deactivate
        self.Closing += self.Form_Closing
        self.Resize += self.Form_Resize

        self.dragStart = None
        self.MouseDown += self.Form_MouseDown
        self.MouseUp += self.Form_MouseUp
        self.MouseMove += self.Form_MouseMove

        self.createDrawingContext()

        # Where are we viewing from?
        self.cameraPos = (0, 0, 12)

        # The current pitch and yaw of the camera
        self.yaw = 0
        self.pitch = 0

        # The change in pitch and yaw from any ongoing drag operations
        self.yawDelta = 0
        self.pitchDelta = 0

        # The near clipping pane (distance from the viewer to the screen)
        self.near = 0.1

        # The far clipping pane (stuff beyond this is not visible)
        self.far = 100

        # Vertical field of view (in degrees)
        self.fovY = 45

        # Field of view (in units at screen distance on the y axis)
        self.fovYU = 2 * self.near * math.tan(math.radians(self.fovY / 2))

        self.xrot = 0
        self.xspeed = 0.2

        self.yrot = 0
        self.yspeed = 0.2

        self.positions = [(0, 0, 0)]
        self.positionIndex = 0


    def Form_Activated(self, sender, event):
        self.active = True


    def Form_Deactivate(self, sender, event):
        self.active = False


    def Form_Closing(self, sender, event):
        self.done = True


    def Form_Resize(self, sender, event):
        self.resizeGLScene(self.Width, self.Height)


    def Form_MouseDown(self, sender, event):
        if event.Button != MouseButtons.Left:
            return
        self.dragStart = event.X, event.Y
        self.yawDelta = 0
        self.pitchDelta = 0


    def Form_MouseUp(self, sender, event):
        self.dragStart = None
        self.yaw += self.yawDelta
        self.pitch += self.pitchDelta
        self.yawDelta = 0
        self.pitchDelta = 0


    def Form_MouseMove(self, sender, event):
        if not self.dragStart:
            return
        startX, startY = self.dragStart
        endX, endY = event.X, event.Y
        pixelsToUnitsAtScreen = self.fovYU / self.Height

        startX -= self.Width / 2
        startX *= pixelsToUnitsAtScreen
        endX -= self.Width / 2
        endX *= pixelsToUnitsAtScreen

        self.yawDelta = math.degrees(math.asin(endX / self.near) - math.asin(startX / self.near))

        startY -= self.Height / 2
        startY *= pixelsToUnitsAtScreen
        endY -= self.Height / 2
        endY *= pixelsToUnitsAtScreen

        self.pitchDelta = math.degrees(math.asin(endY / self.near) - math.asin(startY / self.near))




    def createDrawingContext(self):
        self.hDC = None
        self.hRC = None

        pfd = Gdi.PIXELFORMATDESCRIPTOR(
            nSize = Int16(Marshal.SizeOf(Gdi.PIXELFORMATDESCRIPTOR)),
            nVersion = Int16(1),
            dwFlags = Gdi.PFD_DRAW_TO_WINDOW | Gdi.PFD_SUPPORT_OPENGL | Gdi.PFD_DOUBLEBUFFER,
            iPixelType = Byte(Gdi.PFD_TYPE_RGBA),
            cColorBits = Byte(16),
            cRedBits = Byte(0),
            cRedShift = Byte(0),
            cGreenBits = Byte(0),
            cGreenShift = Byte(0),
            cBlueBits = Byte(0),
            cBlueShift = Byte(0),
            cAlphaBits = Byte(0),
            cAlphaShift = Byte(0),
            cAccumBits = Byte(0),
            cAccumRedBits = Byte(0),
            cAccumGreenBits = Byte(0),
            cAccumBlueBits = Byte(0),
            cAccumAlphaBits = Byte(0),
            cDepthBits = Byte(16),
            cStencilBits = Byte(0),
            cAuxBuffers = Byte(0),
            iLayerType = Byte(Gdi.PFD_MAIN_PLANE),
            bReserved = Byte(0),
            dwLayerMask = 0,
            dwVisibleMask = 0,
            dwDamageMask = 0
        )

        self.hDC = User.GetDC(self.Handle)
        if self.hDC == IntPtr.Zero:
            self.killGLWindow()
            raise Exception("Can't get DC")

        pixelFormat, pfd = Gdi.ChoosePixelFormat(self.hDC, pfd)
        if not pixelFormat:
            self.killGLWindow()
            raise Exception("Can't Find A Suitable PixelFormat")

        if not Gdi.SetPixelFormat(self.hDC, pixelFormat, pfd):
            self.killGLWindow()
            raise Exception("Can't Set The PixelFormat")

        self.hRC = Wgl.wglCreateContext(self.hDC)
        if self.hRC == IntPtr.Zero:
            self.killGLWindow()
            raise Exception("Can't Create A GL Rendering Context")

        if not Wgl.wglMakeCurrent(self.hDC, self.hRC):
            self.killGLWindow()
            raise Exception("Can't Activate The GL Rendering Context.")


    def killGLWindow(self):
        if self.hRC != IntPtr.Zero:
            if not Wgl.wglMakeCurrent(IntPtr.Zero, IntPtr.Zero):
                raise Exception("Release Of DC And RC Failed.")

            if not Wgl.wglDeleteContext(self.hRC):
                raise Exception("Release Rendering Context Failed.")

            self.hRC = IntPtr.Zero

        if not self.hDC != IntPtr.Zero:
            if not self.IsDisposed:
                if self.Handle != IntPtr.Zero:
                    if not User.ReleaseDC(form.Handle, self.hDC):
                        raise Exception("Release Device Context Failed.")

            self.hDC = IntPtr.Zero

        self.Hide()
        self.Close()


    def resizeGLScene(self, width, height):
        if height == 0:
            height = 1

        Gl.glViewport(0, 0, width, height)
        Gl.glMatrixMode(Gl.GL_PROJECTION)
        Gl.glLoadIdentity()
        Glu.gluPerspective(self.fovY, width / float(height), self.near, self.far)
        Gl.glMatrixMode(Gl.GL_MODELVIEW)
        Gl.glLoadIdentity()



    def Show(self):
        Form.Show(self)
        self.resizeGLScene(self.Width, self.Height)

        self.initGL()


    def initGL(self):
        self.loadGLTextures()

        lightAmbient = Array[Single]([0.5, 0.5, 0.5, 1])
        lightDiffuse = Array[Single]([1, 1, 1, 1])
        lightPosition = Array[Single]([0, 0, 2, 1])

        Gl.glEnable(Gl.GL_TEXTURE_2D)
        Gl.glShadeModel(Gl.GL_SMOOTH)
        Gl.glClearColor(0, 0, 0, 0.5)
        Gl.glClearDepth(1)
        Gl.glEnable(Gl.GL_DEPTH_TEST)
        Gl.glDepthFunc(Gl.GL_LEQUAL)
        Gl.glHint(Gl.GL_PERSPECTIVE_CORRECTION_HINT, Gl.GL_NICEST)
        Gl.glLightfv.Overloads[int, int, Array[Single]](Gl.GL_LIGHT1, Gl.GL_AMBIENT, lightAmbient)
        Gl.glLightfv.Overloads[int, int, Array[Single]](Gl.GL_LIGHT1, Gl.GL_DIFFUSE, lightDiffuse)
        Gl.glLightfv.Overloads[int, int, Array[Single]](Gl.GL_LIGHT1, Gl.GL_POSITION, lightPosition)
        Gl.glEnable(Gl.GL_LIGHT1)
        Gl.glEnable(Gl.GL_LIGHTING)



    def loadGLTextures(self):
        textureImage = Image.FromFile(path.join(path.dirname(__file__), "texture.bmp"))
        textureImage.RotateFlip(RotateFlipType.RotateNoneFlipY)
        rectangle = Rectangle(0, 0, textureImage.Width, textureImage.Height)
        bitmapData = textureImage.LockBits(rectangle, ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb)
        try:

            textures = Array[int]([0])
            Gl.glGenTextures.Overloads[int, Array[int]](1, textures)
            self.texture = textures[0]

            Gl.glBindTexture(Gl.GL_TEXTURE_2D, self.texture)
            Gl.glTexParameteri(Gl.GL_TEXTURE_2D, Gl.GL_TEXTURE_MAG_FILTER, Gl.GL_LINEAR)
            Gl.glTexParameteri(Gl.GL_TEXTURE_2D, Gl.GL_TEXTURE_MIN_FILTER, Gl.GL_LINEAR_MIPMAP_NEAREST)
            Glu.gluBuild2DMipmaps(Gl.GL_TEXTURE_2D, Gl.GL_RGB8, textureImage.Width, textureImage.Height, Gl.GL_BGR, Gl.GL_UNSIGNED_BYTE, bitmapData.Scan0)
        finally:
            textureImage.UnlockBits(bitmapData)
            textureImage.Dispose()


    def drawGLScene(self):
        Gl.glClear(Gl.GL_COLOR_BUFFER_BIT | Gl.GL_DEPTH_BUFFER_BIT)
        Gl.glLoadIdentity()
        Gl.glRotatef(-self.yaw - self.yawDelta, 0, 1, 0)
        Gl.glRotatef(-self.pitch - self.pitchDelta, 1, 0, 0)
        cX, cy, cZ = self.cameraPos
        Gl.glTranslatef(-cX, -cy, -cZ)

        if self.positionIndex >= len(self.positions):
            self.positionIndex = 0
        position = self.positions[self.positionIndex]
        Gl.glTranslatef(*position)
        self.positionIndex += 1

        Gl.glRotatef(self.xrot, 1, 0, 0)
        Gl.glRotatef(self.yrot, 0, 1, 0)

        Gl.glBindTexture(Gl.GL_TEXTURE_2D, self.texture)

        Gl.glBegin(Gl.GL_QUADS);
        # Front Face
        Gl.glNormal3f(0, 0, 1);
        Gl.glTexCoord2f(0, 0); Gl.glVertex3f(-1, -1, 1);
        Gl.glTexCoord2f(1, 0); Gl.glVertex3f(1, -1, 1);
        Gl.glTexCoord2f(1, 1); Gl.glVertex3f(1, 1, 1);
        Gl.glTexCoord2f(0, 1); Gl.glVertex3f(-1, 1, 1);
        # Back Face
        Gl.glNormal3f(0, 0, -1);
        Gl.glTexCoord2f(1, 0); Gl.glVertex3f(-1, -1, -1);
        Gl.glTexCoord2f(1, 1); Gl.glVertex3f(-1, 1, -1);
        Gl.glTexCoord2f(0, 1); Gl.glVertex3f(1, 1, -1);
        Gl.glTexCoord2f(0, 0); Gl.glVertex3f(1, -1, -1);
        # Top Face
        Gl.glNormal3f(0, 1, 0);
        Gl.glTexCoord2f(0, 1); Gl.glVertex3f(-1, 1, -1);
        Gl.glTexCoord2f(0, 0); Gl.glVertex3f(-1, 1, 1);
        Gl.glTexCoord2f(1, 0); Gl.glVertex3f(1, 1, 1);
        Gl.glTexCoord2f(1, 1); Gl.glVertex3f(1, 1, -1);
        # Bottom Face
        Gl.glNormal3f(0, -1, 0);
        Gl.glTexCoord2f(1, 1); Gl.glVertex3f(-1, -1, -1);
        Gl.glTexCoord2f(0, 1); Gl.glVertex3f(1, -1, -1);
        Gl.glTexCoord2f(0, 0); Gl.glVertex3f(1, -1, 1);
        Gl.glTexCoord2f(1, 0); Gl.glVertex3f(-1, -1, 1);
        # Right face
        Gl.glNormal3f(1, 0, 0);
        Gl.glTexCoord2f(1, 0); Gl.glVertex3f(1, -1, -1);
        Gl.glTexCoord2f(1, 1); Gl.glVertex3f(1, 1, -1);
        Gl.glTexCoord2f(0, 1); Gl.glVertex3f(1, 1, 1);
        Gl.glTexCoord2f(0, 0); Gl.glVertex3f(1, -1, 1);
        # Left Face
        Gl.glNormal3f(-1, 0, 0);
        Gl.glTexCoord2f(0, 0); Gl.glVertex3f(-1, -1, -1);
        Gl.glTexCoord2f(1, 0); Gl.glVertex3f(-1, -1, 1);
        Gl.glTexCoord2f(1, 1); Gl.glVertex3f(-1, 1, 1);
        Gl.glTexCoord2f(0, 1); Gl.glVertex3f(-1, 1, -1);
        Gl.glEnd()

        self.xrot += self.xspeed
        self.yrot += self.yspeed



    def run(self):
        try:
            while not self.done:
                Application.DoEvents()

                self.drawGLScene()
                Gdi.SwapBuffers(self.hDC)
        finally:
            self.killGLWindow()



def CreateBackgroundSpinningBoxWindow(title, width, height):
    class Runner(object):
        def __init__(self):
            self.windowReady = ManualResetEvent(False)
            self.window = None

        def run(self):
            self.window = SpinningBoxWindow(title, width, height)
            self.window.Show()
            self.windowReady.Set()
            self.window.run()

    runner = Runner()
    thread = Thread(ThreadStart(runner.run))
    thread.SetApartmentState(ApartmentState.STA)
    thread.Start()
    runner.windowReady.WaitOne()

    return runner.window



if __name__ == "__main__":
    #window = CreateBackgroundSpinningBoxWindow("OpenGL Window",1024, 768)
    window = SpinningBoxWindow("OpenGL Window",1024, 768)
    window.Show()
    window.run()
