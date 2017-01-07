#!/usr/bin/python
# coding:utf-8

from Datentypen import Foto, Einstellungen
from threading import Thread, Lock
from urllib import urlopen
from datetime import datetime, timedelta
from os.path import realpath, dirname, isdir
from os import devnull, mkdir
from errno import EEXIST
from subprocess import call
from time import sleep
from Tkinter import *
from tkFileDialog import askdirectory
from PIL import ImageTk as PIL_ImageTk, Image as PIL_Image


PATH = dirname(realpath(__file__)) + "/"
LOCK = Lock()


class SettingsWindow(object):
    def __init__(self, settings=None):
        def ok():
            self.settings.remoteOrdner = self.entryRemDirText.get()

            tmp = self.buttonLocDirText.get()
            while tmp.endswith("/"):
                tmp = tmp[:-1]
            if not tmp.endswith("FotoboxDownload"):
                tmp += "/FotoboxDownload"
            try:
                mkdir(tmp, 0o770)
            except OSError as e:
                if e.errno == EEXIST and isdir(tmp):
                    pass
                else:
                    self.tk.destroy()
                    raise
            self.settings.lokalOrdner = tmp

            self.settings.anzeigedauerSek = self.dropImgDurInt.get()
            self.settings.downloadVerzoegerungMin = self.dropImgDelayInt.get()
            self.settings.speichern()
            self.tk.destroy()

        def chooseLocDir():
            dname = askdirectory()
            if dname:
                self.buttonLocDirText.set(dname)
        if settings is None:
            self.settings = Einstellungen.get()
        else:
            self.settings = settings
        self.tk = Tk()
        self.tk.resizable(width=False, height=False)
        self.tk.title("Fotobox Einstellungen")

        # Remoteordnereingabe
        self.labelRemDir = Label(self.tk, text="Kameraordner:")
        self.labelRemDir.grid(row=0, column=0, sticky=W)
        self.entryRemDirText = StringVar(self.tk, self.settings.remoteOrdner)
        self.entryRemDir = Entry(self.tk, relief=SUNKEN, textvariable=self.entryRemDirText)
        self.entryRemDir.grid(row=0, column=1, sticky=W)

        # Lokalordnerauswahl
        self.labelLocDir = Label(self.tk, text="Bilderordner:")
        self.labelLocDir.grid(row=1, column=0, sticky=W)
        self.buttonLocDirText = StringVar(self.tk, self.settings.lokalOrdner)
        self.buttonLocDir = Button(self.tk, textvariable=self.buttonLocDirText, command=chooseLocDir)
        self.buttonLocDir.grid(row=1, column=1, sticky=W)

        # Anzeigedauer
        self.labelImgDur = Label(self.tk, text="Anzeigedauer (s):")
        self.labelImgDur.grid(row=2, column=0, sticky=W)
        self.dropImgDurInt = IntVar(self.tk, self.settings.anzeigedauerSek)
        self.dropImgDur = OptionMenu(self.tk, self.dropImgDurInt, 5, 10, 20, 30, 45, 60)
        self.dropImgDur.grid(row=2, column=1, sticky=W)

        # Anzeigeverzögerung
        self.labelImgDelay = Label(self.tk, text="Downloadverzögerung (m):")
        self.labelImgDelay.grid(row=3, column=0, sticky=W)
        self.dropImgDelayInt = IntVar(self.tk, self.settings.downloadVerzoegerungMin)
        self.dropImgDelay = OptionMenu(self.tk, self.dropImgDelayInt, 0, 1, 2, 3, 5, 10)
        self.dropImgDelay.grid(row=3, column=1, sticky=W)

        self.buttonOK = Button(self.tk, text="OK", command=ok).grid(row=4, column=0)

        self.tk.mainloop()


class Syncer(Thread):
    CAM_DEST = "flashair"
    CAM_URL = "http://{0}/".format(CAM_DEST)
    CAM_CMD = "{0}command.cgi?".format(CAM_URL)
    CAM_UPL = "{0}upload.cgi?".format(CAM_URL)
    CONNECTED = FALSE

    def __init__(self, settings):
        super(Syncer, self).__init__()
        self.daemon = True
        self.settings = settings

    @staticmethod
    def __execute(url):
        try:
            return urlopen(url).read()
        except:
            return None

    def getFotoInfos(self):
        r = Syncer.__execute(Syncer.CAM_CMD + "op=100&DIR={0}".format(self.settings.remoteOrdner))
        if r is not None:
            return [i for i in r.split("\r\n")[1:] if i != ""]
        return []

    @staticmethod
    def loescheRemoteFoto(pfad):
        return urlopen(Syncer.CAM_UPL + "DEL={0}".format(pfad)).read().strip() == "SUCCESS"

    @staticmethod
    def syncFotoDateien(lokalpfad):
        for f in Foto.alleLaden():
            try:
                open(f.lokalPfad, "rb").close()
            except IOError:
                f.loeschen()
            else:
                if lokalpfad != dirname(f.lokalPfad):
                    f.loeschen()
        if Syncer.CONNECTED:
            for f in Foto.ladeRemote():
                if Syncer.loescheRemoteFoto(f.remoteOhneRoot):
                    f.istRemote = False
                    f.speichern()

    def run(self):
        while True:
            # Warten, bis Verbindung zur IP der Karte hergestellt werden kann; Status speichern
            with open(devnull, "wb") as dNull:
                while call(["ping", "-c", "1", "-W", "2", Syncer.CAM_DEST], stdout=dNull, stderr=dNull):
                    LOCK.acquire()
                    Syncer.CONNECTED = False
                    LOCK.release()
                    sleep(10)
                LOCK.acquire()
                Syncer.CONNECTED = True
                LOCK.release()

            try:
                # Identifier ist eine Kombination aus Aufnahmedatum und Remotepfad einer Fotodatei.
                # Es wird davon ausgegangen, dass nicht innerhalb von zwei Sekunden zwei Dateien
                # mit demselben Namen in der Kamera erstellt werden (die Auflösung des Zeitstempels
                # der FlashAir ist zwei Sekunden).
                identifierDict = Foto.ladeAlleIdentifier()
                fIds = identifierDict.keys()

                # Heruntergeladene Informationen in Foto-Objekt konvertieren. Obj==None bedeutet, dass unpassende
                # Informationen heruntergeladen wurden, z.B. wenn ein Foto schreibgeschützt ist.
                remoteFotos = [Foto.konvertiereRemote(l, Syncer.CAM_URL) for l in self.getFotoInfos()]
                remoteFotos = [f for f in remoteFotos if f is not None]

                for f in remoteFotos:
                    # Foto ist noch nicht in der Datenbank.
                    if not (f.getIdentifier() in fIds):
                        if f.aufnDatum + timedelta(minutes=self.settings.downloadVerzoegerungMin) < datetime.today():
                            if f.download(self.settings.lokalOrdner):
                                # Foto bei erfolgreichem Download in die Datenbank speichern und versuchen,
                                # es von der FlashAir zu löschen.
                                f.speichernUnter()
                                if Syncer.loescheRemoteFoto(f.remoteOhneRoot):
                                # Foto konnte gelöscht werden; diese Information in die DB schreiben.
                                    f.istRemote = False
                                    f.speichern()
                    # Foto ist bereits in der Datenbank, bug Canon || FlashAir; erneut zum Löschen markieren
                    else:
                        fDb = Foto.laden(identifierDict[f.getIdentifier()])
                        fDb.istRemote = True
                        fDb.speichern()
                # Gelöschte lokale Fotos aus der Datenbank entfernen, nicht gelöschte Remotefotos löschen.
                Syncer.syncFotoDateien(self.settings.lokalOrdner)
            except Exception as e:
                s = ""
                for k in sorted(e.__dict__.keys()):
                    s += "{0}:\n{1}{2}".format(k, 4*" ", e.__dict__[k])
                    print s
            sleep(5)


class ImageRefresher(Thread):
    def __init__(self, viewer):
        super(ImageRefresher, self).__init__()
        self.daemon = True
        self.viewer = viewer
        self.res = self.viewer.getXY()
        self.quit = False

    def isNewRes(self):
        return self.res != self.viewer.getXY()

    def refreshRes(self):
        self.res = self.viewer.getXY()

    def run(self):
        while not self.quit:
            if self.isNewRes():
                LOCK.acquire()
                sleep(.1)
                self.refreshRes()
                self.viewer.displayImage()
                LOCK.release()
            sleep(.01)


class ImageLoader(Thread):
    def __init__(self, viewer, settings):
        super(ImageLoader, self).__init__()
        self.daemon = True
        self.viewer = viewer
        self.settings = settings
        self.quit = False

    def run(self):
        while not self.quit:
            pics = Foto.alleLaden(orderBy="zeigDatum")
            if pics:
                self.viewer.displayImage(pics[0].lokalPfad)
                pics[0].zeigDatum = datetime.today()
                pics[0].speichern()
            sleep(self.settings.anzeigedauerSek)


class ImageViewer(object):
    def __init__(self):
        self.tk = Tk()
        self.tk.geometry("500x500+10+10")
        self.tk.configure(background="black")
        self.isFullscreen = False
        self.tk.bind("<F11>", self.toggleFS)
        self.tk.bind("<Escape>", self.quitFS)
        self.tk.title("Fotobox Viewer")
        self.img = None
        self.imgLabel = None
        self.currentImagePath = None

    def toggleFS(self, event=None):
        self.isFullscreen = not self.isFullscreen
        self.setFS()
        return "break"

    def quitFS(self, event=None):
        self.isFullscreen = False
        self.setFS()
        return "break"

    def setFS(self):
        self.tk.attributes("-fullscreen", self.isFullscreen)

    def getGeometry(self):
        return self.tk.winfo_geometry()

    def getXY(self):
        strings = self.getGeometry().split("+")[0].split("x")
        return int(strings[0]), int(strings[1])

    def displayImage(self, localPath=None):
        if localPath is not None:
            self.currentImagePath = localPath

        if self.currentImagePath is not None:
            x, y = self.getXY()
            pic = PIL_Image.open(self.currentImagePath)
            ratio = min(float(x)/pic.size[0], float(y)/pic.size[1])
            pic = pic.resize((max(int(ratio*pic.size[0]), 1),
                              max(int(ratio*pic.size[1]), 1)),
                             PIL_Image.ANTIALIAS)
            self.img = PIL_ImageTk.PhotoImage(pic)
            if self.imgLabel is not None:
                self.imgLabel.destroy()
            self.imgLabel = Label(self.tk, image=self.img, background="black")
            self.imgLabel.pack()


class Main(object):
    def __init__(self):
        SettingsWindow()
        self.settings = Einstellungen.get()
        Syncer.syncFotoDateien(self.settings.lokalOrdner)
        self.syncer = Syncer(self.settings)
        self.syncer.start()

        self.imageViewer = ImageViewer()
        self.imageLoader = ImageLoader(self.imageViewer, self.settings)
        self.imageRefresher = ImageRefresher(self.imageViewer)
        self.imageLoader.start()
        self.imageRefresher.start()
        self.imageViewer.tk.mainloop()


if __name__ == "__main__":
    Main()
