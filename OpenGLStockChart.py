import clr
#clr.AddReference("System.Drawing")
#clr.AddReference("System.Windows.Forms")
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


glLightfv = Gl.glLightfv.Overloads[int, int, Array[Single]]


class ChartWindow(Form):

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

        self.dragging = False
        self.dragLastPosition = None
        self.MouseDown += self.Form_MouseDown
        self.MouseUp += self.Form_MouseUp
        self.MouseMove += self.Form_MouseMove
        self.MouseWheel += self.Form_MouseWheel

        self.createDrawingContext()

        # Where are we viewing from?
        self.cameraDistance = 30

        # The orientation of the camera, expressed as a matrix
        self.cameraRotationMatrix = Array.CreateInstance(Single, 16)

        # The near clipping pane (distance from the viewer to the screen)
        self.near = 0.1

        # The far clipping pane (stuff beyond this is not visible)
        self.far = 5000

        # Vertical field of view (in degrees)
        self.fovY = 45

        # Field of view (in units at screen distance on the y axis)
        self.fovYU = 2 * self.near * math.tan(math.radians(self.fovY / 2))

        # Initial empty chart data
        self.callList = None


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
        self.dragging = True
        self.dragLastPosition = event.X, event.Y


    def Form_MouseUp(self, sender, event):
        if event.Button != MouseButtons.Left:
            return
        if self.dragging:
            self.dragging = False
            self.dragLastPosition = None



    def Form_MouseMove(self, sender, event):
        if self.dragging:
            nowX, nowY = event.X, event.Y
            thenX, thenY = self.dragLastPosition
            deltaX = nowX - thenX
            deltaY = nowY - thenY

            Gl.glPushMatrix()
            Gl.glLoadIdentity()
            Gl.glRotatef(float(deltaX) / (360. / self.fovY), 0, 1, 0)
            Gl.glRotatef(float(deltaY) / (360. / self.fovY), 1, 0, 0)
            Gl.glMultMatrixf(self.cameraRotationMatrix)
            self.glGetFloatv(Gl.GL_MODELVIEW_MATRIX, self.cameraRotationMatrix)
            Gl.glPopMatrix()

            self.dragLastPosition = nowX, nowY


    def Form_MouseWheel(self, sender, event):
        self.cameraDistance -= event.Delta / 100


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
        Gl.glEnable(Gl.GL_TEXTURE_2D)
        Gl.glShadeModel(Gl.GL_SMOOTH)
        Gl.glClearColor(0, 0, 0, 0.5)
        Gl.glClearDepth(1)
        Gl.glEnable(Gl.GL_DEPTH_TEST)
        Gl.glDepthFunc(Gl.GL_LEQUAL)
        Gl.glHint(Gl.GL_PERSPECTIVE_CORRECTION_HINT, Gl.GL_NICEST)

        Gl.glPushMatrix()
        Gl.glLoadIdentity()
        Gl.glRotatef(-30, 1, 0, 0)
        self.glGetFloatv = Gl.glGetFloatv.Overloads[int, type(self.cameraRotationMatrix)]
        self.glGetFloatv(Gl.GL_MODELVIEW_MATRIX, self.cameraRotationMatrix)
        Gl.glPopMatrix()


    def drawGLScene(self):
        Gl.glClear(Gl.GL_COLOR_BUFFER_BIT | Gl.GL_DEPTH_BUFFER_BIT)
        Gl.glEnable(Gl.GL_NORMALIZE)

        Gl.glLoadIdentity()

        Gl.glTranslatef(0, 0, -self.cameraDistance)
        Gl.glMultMatrixf(self.cameraRotationMatrix)

        glLightfv(Gl.GL_LIGHT1, Gl.GL_AMBIENT, Array[Single]([0.3, 0.3, 0.3, 1]))
        glLightfv(Gl.GL_LIGHT1, Gl.GL_DIFFUSE, Array[Single]([1, 1, 1, 1]))
        glLightfv(Gl.GL_LIGHT1, Gl.GL_POSITION, Array[Single]([100, 100, -100, 1]))
        Gl.glEnable(Gl.GL_LIGHT1)
        Gl.glEnable(Gl.GL_LIGHTING)

        numStocks = len(self.stocks)
        for stockNum, (stock, stockName, (r, g, b)) in enumerate(self.stocks):
            Gl.glBegin(Gl.GL_TRIANGLE_STRIP)
            Gl.glMaterialfv(Gl.GL_FRONT, Gl.GL_AMBIENT, Array[Single]([r / 512., g / 512., b / 512., 1]))
            Gl.glMaterialfv(Gl.GL_FRONT, Gl.GL_DIFFUSE, Array[Single]([r / 256., g / 256., b / 256., 1]))
            firstPrice = None
            lastVertex = None
            for dateNum, date in enumerate(self.dates):
                closePrice = self.stockData[stock, date]
                if closePrice:
                    if firstPrice is None:
                        firstPrice = closePrice
                    # Normalise such that the first price we see is 100,
                    # then make sure that the 3D origin is the starting point
                    # halfway through the set of stocks
                    closePrice = (closePrice / firstPrice) * 100
                    cX, cY, cZ = stockNum - numStocks / 2, closePrice - 100, -dateNum
                    if lastVertex is None:
                        Gl.glNormal3f(0, 1, 0)
                    else:
                        lX, lY, lZ = lastVertex
                        Gl.glNormal3f(0, cY - lY, cZ - lZ)
                    Gl.glVertex3f(cX, cY, cZ)
                    Gl.glVertex3f(cX + 1, cY, cZ)
                    lastVertex = cX, cY, cZ
            Gl.glEnd()



    def update(self, stocks, dates, stockData):
        self.stocks = stocks
        self.dates = dates
        self.stockData = stockData



    def run(self):
        try:
            while not self.done:
                Application.DoEvents()

                self.drawGLScene()
                Gdi.SwapBuffers(self.hDC)
        finally:
            self.killGLWindow()



def CreateOpenGLStockChart(title, width, height):
    class Runner(object):
        def __init__(self):
            self.windowReady = ManualResetEvent(False)
            self.window = None

        def run(self):
            try:
                self.window = ChartWindow(title, width, height)
                self.window.Show()
                self.windowReady.Set()
                self.window.run()
            except Exception, e:
                print e

    runner = Runner()
    thread = Thread(ThreadStart(runner.run))
    thread.SetApartmentState(ApartmentState.STA)
    thread.Start()
    runner.windowReady.WaitOne()

    return runner.window


