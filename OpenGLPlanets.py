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


SUNLIGHT_AMBIENT = Array[Single]([0.3, 0.3, 0.3, 1])
SUNLIGHT_DIFFUSE = Array[Single]([1, 1, 0.5, 1])
SUN_POSITION = Array[Single]([0, 0, 0, 1])


PLANET_SPECULAR = 0
PLANET_SHININESS = 0
PLANET_EMISSION_COLOUR = Array[Single]([0, 0, 0, 0])

glLightfv = Gl.glLightfv.Overloads[int, int, Array[Single]]


class Planet(object):
    def __init__(self, radius, radiusScale, colour, daysPerTick, ringsFunction, positions):
        self.radius = radius
        self.radiusScale = radiusScale
        self.colour = colour
        self.ambientColour = Array[Single]([self.colour.R / 512., self.colour.G / 512., self.colour.B / 512., 1])
        self.diffuseColour = Array[Single]([self.colour.R / 256., self.colour.G / 256., self.colour.B / 256., 1])
        self.daysPerTick = daysPerTick
        self.ringsFunction = ringsFunction
        self.positions = positions


    def convertPosition(self, (x, y, z), distanceScale):
        return x / distanceScale, y / distanceScale, z / distanceScale


    def draw(self, distanceScale, days):
        Gl.glPushMatrix()
        positionIndex = int(days / self.daysPerTick)
        positionIndex %= len(self.positions)
        x, y, z = self.convertPosition(self.positions[positionIndex], distanceScale)

        planetRadius = self.radiusScale * self.radius / distanceScale

        Gl.glTranslatef(x, y, z)

        quad = Glu.gluNewQuadric()
        Gl.glMaterialfv(Gl.GL_FRONT, Gl.GL_AMBIENT, self.ambientColour)
        Gl.glMaterialfv(Gl.GL_FRONT, Gl.GL_DIFFUSE, self.diffuseColour)
        Gl.glMaterialfv(Gl.GL_FRONT, Gl.GL_SPECULAR, PLANET_SPECULAR)
        Gl.glMaterialf(Gl.GL_FRONT, Gl.GL_SHININESS, PLANET_SHININESS)
        Gl.glMaterialfv(Gl.GL_FRONT, Gl.GL_EMISSION, PLANET_EMISSION_COLOUR)
        Glu.gluSphere(quad, planetRadius, 40, 40)
        Glu.gluDeleteQuadric(quad)

        if self.ringsFunction:
            self.ringsFunction(self.radiusScale / distanceScale)

        Gl.glPopMatrix()

        Gl.glBegin(Gl.GL_POINTS)
        Gl.glColor3f(1, 1, 1)
        for position in self.positions:
            Gl.glVertex3f(*self.convertPosition(position, distanceScale))
        Gl.glEnd()



class OrreryWindow(Form):

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
        self.MouseWheel += self.Form_MouseWheel

        self.KeyPress += self.Form_KeyPress

        self.createDrawingContext()

        # Where are we viewing from?
        self.cameraPos = (0, 0, 12)

        # The current roll of the solar system
        self.rollX = 0
        self.rollY = 0

        # The change in roll from any ongoing drag operations
        self.rollXDelta = 0
        self.rollYDelta = 0

        # The near clipping pane (distance from the viewer to the screen)
        self.near = 0.1

        # The far clipping pane (stuff beyond this is not visible)
        self.far = 5000

        # Vertical field of view (in degrees)
        self.fovY = 45

        # Field of view (in units at screen distance on the y axis)
        self.fovYU = 2 * self.near * math.tan(math.radians(self.fovY / 2))

        # How much should we scale planetary distances?
        self.distanceScale = 10000000

        # How many days into the simulation are we?
        self.days = 0

        # How many days do we advance for each frame
        self.daysPerFrame = 1




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
        self.rollXDelta = 0
        self.rollYDelta = 0


    def Form_MouseUp(self, sender, event):
        self.dragStart = None
        self.rollX += self.rollXDelta
        self.rollY += self.rollYDelta
        self.rollXDelta = 0
        self.rollYDelta = 0


    def Form_MouseMove(self, sender, event):
        if not self.dragStart:
            return
        startX, startY = self.dragStart
        endX, endY = event.X, event.Y

        # Dragging up and down rolls the solar system around the X axis,
        # and from side to side around the Y axis.
        self.rollXDelta = (startY - endY) / 10
        self.rollYDelta = (startX - endX) / 10


    def Form_MouseWheel(self, sender, event):
        self.cameraPos = self.cameraPos[0], self.cameraPos[1], self.cameraPos[2] - event.Delta / 10



    def Form_KeyPress(self, sender, event):
        if event.KeyChar in ("+", "="):
            self.cameraPos = self.cameraPos[0], self.cameraPos[1], self.cameraPos[2] - 10
        if event.KeyChar in ("-", "_"):
            self.cameraPos = self.cameraPos[0], self.cameraPos[1], self.cameraPos[2] + 10


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

        # Create a light to represent the sun
        glLightfv(Gl.GL_LIGHT1, Gl.GL_AMBIENT, SUNLIGHT_AMBIENT)
        glLightfv(Gl.GL_LIGHT1, Gl.GL_DIFFUSE, SUNLIGHT_DIFFUSE)
        Gl.glEnable(Gl.GL_LIGHT1)
        Gl.glEnable(Gl.GL_LIGHTING)


    def goToSun(self):
        Gl.glLoadIdentity()
        cX, cy, cZ = self.cameraPos
        Gl.glTranslatef(-cX, -cy, -cZ)
        Gl.glRotatef(self.rollX + self.rollXDelta, 1, 0, 0)
        Gl.glRotatef(self.rollY + self.rollYDelta, 0, 1, 0)


    def cameraDistance(self):
        cX, cy, cZ = self.cameraPos
        return math.sqrt(cX ** 2 + cy ** 2 + cZ ** 2)


    def drawGLScene(self):
        Gl.glClear(Gl.GL_COLOR_BUFFER_BIT | Gl.GL_DEPTH_BUFFER_BIT)

        self.goToSun()
        glLightfv(Gl.GL_LIGHT1, Gl.GL_POSITION, SUN_POSITION)

        # Now draw the Sun
        quad = Glu.gluNewQuadric()
        Gl.glMaterialfv(Gl.GL_FRONT, Gl.GL_EMISSION, SUNLIGHT_DIFFUSE);
        # Make the sun always visible, even if we're so far away that we can't see it!
        # Simple calculation just makes sure it always subtends at least 0.05 degrees.
        sunRadius = 1392000 / self.distanceScale
        minRadius = 2 * self.cameraDistance() * math.sin(2 * math.pi * 0.025 / 360)
        sunRadius = max(sunRadius, minRadius)
        Glu.gluSphere(quad, sunRadius, 40, 40)
        Glu.gluDeleteQuadric(quad)

        for planet in self.planets:
            planet.draw(self.distanceScale, self.days)

        self.days += self.daysPerFrame


    def run(self):
        try:
            while not self.done:
                Application.DoEvents()

                self.drawGLScene()
                Gdi.SwapBuffers(self.hDC)
        finally:
            self.killGLWindow()



def CreateBackgroundOrreryWindow(title, width, height):
    class Runner(object):
        def __init__(self):
            self.windowReady = ManualResetEvent(False)
            self.window = None

        def run(self):
            try:
                self.window = OrreryWindow(title, width, height)
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


