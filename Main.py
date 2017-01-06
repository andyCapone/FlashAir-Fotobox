#!/usr/bin/python
# coding:utf-8


from Datentypen import Foto
from threading import Thread, Lock
from urllib import urlopen
from datetime import datetime, timedelta
from os.path import realpath, dirname
from os import devnull
from subprocess import call
from time import sleep
from Tkinter import *
from PIL import ImageTk as PIL_ImageTk, Image as PIL_Image


PATH = dirname(realpath(__file__)) + "/"
PATH_DOWNLOAD = PATH + "images/"
WARTEZEIT = timedelta(0)
LOCK = Lock()


class Syncer(Thread):
    CAM_IP = "192.168.0.1"
    CAM_URL = "http://{0}/".format(CAM_IP)
    CAM_CMD = "{0}command.cgi?".format(CAM_URL)
    CAM_UPL = "{0}upload.cgi?".format(CAM_URL)
    CAM_DIR = "/DCIM/100CANON"
    LATEST_ACTION_TIME = datetime(1900, 1, 1)
    CONNECTED = FALSE

    def __init__(self):
        super(Syncer, self).__init__()
        self.daemon = True

    @staticmethod
    def __execute(url):
        try:
            return urlopen(url).read()
        except:
            return None

    @staticmethod
    def getFotoInfos():
        r = Syncer.__execute(Syncer.CAM_CMD + "op=100&DIR={0}".format(Syncer.CAM_DIR))
        if r is not None:
            return [i for i in r.split("\r\n")[1:] if i != ""]
        return []

    @staticmethod
    def loescheRemoteFoto(pfad):
        return urlopen(Syncer.CAM_UPL + "DEL={0}".format(pfad)).read().strip() == "SUCCESS"

    @staticmethod
    def syncFotoDateien():
        for f in Foto.alleLaden():
            try:
                open(f.lokalPfad, "rb").close()
            except IOError:
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
                while call(["ping", "-c", "1", "-W", "2", Syncer.CAM_IP], stdout=dNull, stderr=dNull):
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
                remoteFotos = [Foto.konvertiereRemote(l, Syncer.CAM_URL) for l in Syncer.getFotoInfos()]
                remoteFotos = [f for f in remoteFotos if f is not None]

                for f in remoteFotos:
                    # Foto ist noch nicht in der Datenbank.
                    if not (f.getIdentifier() in fIds):
                        if f.aufnDatum + WARTEZEIT < datetime.today():
                            if f.download(PATH_DOWNLOAD):
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
                Syncer.syncFotoDateien()
            except Exception as e:
                s = ""
                for k in sorted(e.__dict__.keys()):
                    s += "{0}:\n{1}{2}".format(k, 4*" ", e.__dict__[k])
                    print s
            sleep(5)


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


class ImageRefresher(Thread):
    def __init__(self, viewer):
        super(ImageRefresher, self).__init__()
        self.daemon = True
        self.viewer = viewer
        self.res = self.viewer.getXY()

    def isNewRes(self):
        return self.res != self.viewer.getXY()

    def refreshRes(self):
        self.res = self.viewer.getXY()

    def run(self):
        while True:
            if self.isNewRes():
                LOCK.acquire()
                sleep(.1)
                self.refreshRes()
                self.viewer.displayImage()
                LOCK.release()
            sleep(.01)


class ImageLoader(Thread):
    def __init__(self, viewer):
        super(ImageLoader, self).__init__()
        self.daemon = True
        self.viewer = viewer

    def run(self):
        while True:
            pics = Foto.alleLaden(orderBy="zeigDatum")
            if pics:
                self.viewer.displayImage(pics[0].lokalPfad)
                pics[0].zeigDatum = datetime.today()
                pics[0].speichern()
            sleep(10)


if __name__ == "__main__":
    Syncer.syncFotoDateien()
    syncer = Syncer()
    syncer.start()

    imageViewer = ImageViewer()
    imageLoader = ImageLoader(imageViewer)
    imageRefresher = ImageRefresher(imageViewer)
    imageLoader.start()
    imageRefresher.start()
    imageViewer.tk.mainloop()
