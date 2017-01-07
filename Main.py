#!/usr/bin/python
# coding:utf-8

from Datentypen import Foto, Einstellungen
from threading import Thread, Lock
from urllib2 import urlopen
from datetime import datetime, timedelta
from os.path import realpath, dirname, isdir, basename
from os import devnull, mkdir, chmod, listdir, stat, remove
from imghdr import what
from stat import S_IRWXU, S_IRGRP
from sys import argv, exit
from errno import EEXIST
from subprocess import call
from time import sleep
from Tkinter import *
from tkFileDialog import askdirectory
from PIL import ImageTk as PIL_ImageTk, Image as PIL_Image


PATH = dirname(realpath(__file__)) + "/"
LOGPATH = PATH + "logs/"
LOGFILE = LOGPATH + datetime.today().strftime("%Y%m%d-%H%M%S") + "_log.txt"
LOCK = Lock()


def printf(msg):
    pMsg = "{0}: {1}\n".format(datetime.today().strftime("%d.%m.%Y, %H:%M:%S"), msg)
    if Einstellungen.get().logging:
        try:
            with open(LOGFILE, "a") as f:
                f.write(pMsg)
        except IOError:
            print("{0}: Kein Zugriff auf Logdatei."
                  .format(datetime.today().strftime("%d.%m.%Y, %H:%M:%S")))
        except Exception as e:
            print("{0}Unbekannter Fehler beim Loggen:\n{1}\n"
                  .format(datetime.today().strftime("%d.%m.%Y, %H:%M:%S"), e))
    print(pMsg)


def desktop():
    s = """[Desktop Entry]
Type=Application
Name=FlashAir-Fotobox
Exec={0}Main.py
Icon={0}fotobox.ico
Terminal=false""".format(PATH)
    p = PATH + "Fotobox.desktop"
    try:
        with open(p, "w") as f:
            f.write(s)
    except IOError:
        printf("Desktopdatei konnte nicht erstellt werden. Keine Schreibrechte im Ordner \"{0}\"?".format(p))
        return False
    except Exception as e:
        printf("Unerwarteter Fehler in Funktion Main.desktop:\n{0}\n".format(e))
        raise
    else:
        chmod(p, S_IRWXU | S_IRGRP)
    return True


class SettingsWindow(object):
    def __init__(self, settings=None):
        def ok():
            self.settings.remoteOrdner = self.entryRemDirText.get()
            tmp = self.buttonLocDirText.get()
            while tmp.endswith("/"):
                tmp = tmp[:-1]
            if not tmp.endswith("FotoboxBilder"):
                tmp += "/FotoboxBilder"
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
            self.settings.logging = self.dropLogText.get() == "Ja"
            self.settings.speichern()
            self.tk.destroy()

        def chooseLocDir():
            dname = askdirectory()
            if dname:
                self.buttonLocDirText.set(dname)

        def close():
            self.tk.destroy()
            exit(0)

        if settings is None:
            self.settings = Einstellungen.get()
        else:
            self.settings = settings
        self.tk = Tk()
        self.tk.resizable(width=False, height=False)
        self.tk.protocol("WM_DELETE_WINDOW", close)
        self.tk.title("Fotobox Einstellungen")
        icon = PIL_Image.open(PATH + "fotobox.ico")
        self.icon = PIL_ImageTk.PhotoImage(icon)
        self.tk.tk.call("wm", "iconphoto", self.tk._w, self.icon)

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

        # Logging
        self.labelLog = Label(self.tk, text="Loggen:")
        self.labelLog.grid(row=4, column=0, sticky=W)
        if self.settings.logging:
            s = "Ja"
        else:
            s = "Nein"
        self.dropLogText = StringVar(self.tk, s)
        self.dropLog = OptionMenu(self.tk, self.dropLogText, "Ja", "Nein")
        self.dropLog.grid(row=4, column=1, sticky=W)

        self.buttonOK = Button(self.tk, text="OK", command=ok).grid(row=5, column=1, sticky=E)

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
        self.quit = False
        self.isRunning = False
        printf("Syncer initialisiert.")

    @staticmethod
    def __execute(url):
        try:
            return urlopen(url).read()
        except:
            return None

    @staticmethod
    def getFotoInfos(remoteOrdner):
        r = Syncer.__execute(Syncer.CAM_CMD + "op=100&DIR={0}".format(remoteOrdner))
        if r is not None:
            return [i for i in r.split("\r\n")[1:] if i != ""]
        return []

    @staticmethod
    def getRemoteFotos(remoteOrdner):
        remoteFotos = [Foto.konvertiereRemote(l, Syncer.CAM_URL) for l in
                       Syncer.getFotoInfos(remoteOrdner)]
        remoteFotos = [f for f in remoteFotos if f is not None]
        return remoteFotos

    @staticmethod
    def loescheRemoteFoto(pfad):
        return urlopen(Syncer.CAM_UPL + "DEL={0}".format(pfad)).read().strip() in ("SUCCESS", "NG")

    @staticmethod
    def versucheRecover(remoteOrdner, foto):
        if Syncer.CONNECTED:
            while remoteOrdner.startswith("/"):
                remoteOrdner = remoteOrdner[1:]
            endung = "." + foto.lokalPfad.rsplit(".", 1)[-1]
            bName = foto.lokalPfad.rsplit("_", 1)[0]
            testRemotePfad = Syncer.CAM_URL + remoteOrdner + "/" + basename(bName + endung)
            if urlopen(testRemotePfad, timeout=5).geturl() == testRemotePfad:
                remoteFotos = Syncer.getRemoteFotos(remoteOrdner)
                testDict = {f.remotePfad: f for f in remoteFotos}
                try:
                    if testDict[testRemotePfad].size == foto.size:
                        foto.remotePfad = testRemotePfad
                        foto.speichern()
                except:
                    return False
                else:
                    return True
            else:
                return False
        else:
            return False

    @staticmethod
    def syncFotoDateien(settings):
        try:
            bekannt = []
            for f in Foto.alleLaden():
                bekannt.append(f.lokalPfad)
                try:
                    open(f.lokalPfad, "rb").close()
                except IOError:
                    printf("Datenbankeintrag wird gelöscht:\n\tid: {0}\n\tPfad: {1}\n\t"
                           "Grund: Fotodatei konnte nicht geöffnet werden.".format(f.id, f.lokalPfad))
                    f.loeschen()
                else:
                    if settings.lokalOrdner != dirname(f.lokalPfad):
                        printf("Datenbankeintrag wird gelöscht:\n\tid: {0}\n\tPfad: {1}\n\t"
                               "Grund: Foto ist nicht im aktuellen Bilderordner.".format(f.id, f.lokalPfad))
                        f.loeschen()
            for f in listdir(settings.lokalOrdner):
                fp = settings.lokalOrdner + "/" + f
                if (fp not in bekannt) and (not isdir(fp)):
                    if what(fp) in Foto.SUPPORTED:
                        fn = Foto.konvertiereLokal(stat(fp), fp)
                        fn.speichern()
                        printf("Neues Foto (nicht heruntergeladen) erkannt:\n\t"
                               "id: {0}\n\tPfad{1}".format(fn.id, fn.lokalPfad))
                    else:
                        try:
                            remove(fp)
                            printf("Nicht unterstützte Datei aus Bilderordner gelöscht:\n\t{0}".format(fp))
                        except IOError:
                            printf("Nicht unterstützte Datei konnte nicht gelöscht werden:\n\t{0}".format(fp))
            if Syncer.CONNECTED:
                for f in Foto.ladeRemote():
                    if Syncer.loescheRemoteFoto(f.getRemoteOhneRoot(Syncer.CAM_URL)):
                        f.istRemote = False
                        f.speichern()
                        printf("Remotedatei wurde gelöscht:\n\t{0}".format(f.remotePfad))
                    else:
                        printf("Remotedatei konnte nicht gelöscht werden:\n\t{0}".format(f.remotePfad))
            for f in Foto.ladeOhneRemote():
                if Syncer.versucheRecover(settings.remoteOrdner, f):
                    printf("Lokale Datei anhand von Name und Größe auf FlashAir identifiziert:\n\t{0}\n\t"
                           "Wird zum Löschen markiert.".format(f.lokalPfad))
                    fn = Foto.laden(f.id)
                    fn.istRemote = True
                    fn.speichern()
        except Exception as e:
            printf("Unerwarteter Fehler in Methode Syncer.syncFotoDateien:\n{0}\n".format(e))

    def quitThread(self):
        self.quit = True

    def run(self):
        self.isRunning = True
        printf("Syncer gestartet.")
        while not self.quit:
            # Warten, bis Verbindung zur IP der Karte hergestellt werden kann; Status speichern
            with open(devnull, "wb") as dNull:
                while call(["ping", "-c", "1", "-W", "2", Syncer.CAM_DEST], stdout=dNull, stderr=dNull):
                    printf("Keine Verbindung zur FlashAir möglich.")
                    Syncer.syncFotoDateien(self.settings)
                    LOCK.acquire()
                    Syncer.CONNECTED = False
                    LOCK.release()
                    end = datetime.today() + timedelta(seconds=10)
                    while datetime.today() < end:
                        sleep(.01)
                        if self.quit:
                            printf("Syncer beendet.")
                            self.isRunning = False
                            return
                LOCK.acquire()
                if not Syncer.CONNECTED:
                    Syncer.CONNECTED = True
                    printf("Verbindung zur FlashAir hergestellt.")
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
                remoteFotos = Syncer.getRemoteFotos(self.settings.remoteOrdner)

                for f in remoteFotos:
                    # Foto ist noch nicht in der Datenbank.
                    if not (f.getIdentifier() in fIds):
                        if f.aufnDatum + timedelta(minutes=self.settings.downloadVerzoegerungMin) < datetime.today():
                            if f.download(self.settings.lokalOrdner):
                                # Foto bei erfolgreichem Download in die Datenbank speichern und versuchen,
                                # es von der FlashAir zu löschen.
                                f.speichern()
                                printf("Neues Foto heruntergeladen und zum Löschen markiert:\n\t{0}"
                                       .format(f.lokalPfad))
                            else:
                                printf("Foto konnte nicht heruntergeladen werden:\n\t{0}".format(f.remotePfad))
                    # Foto ist bereits in der Datenbank, bug Canon || FlashAir; erneut zum Löschen markieren
                    else:
                        fDb = Foto.laden(identifierDict[f.getIdentifier()])
                        fDb.istRemote = True
                        fDb.speichern()
                        printf("Foto wurde erneut zum Löschen markiert:\n\t{0}".format(f.remotePfad))
            except Exception as e:
                printf("Unerwarteter Fehler in Syncer.run:\n\t{0}".format(e))
            Syncer.syncFotoDateien(self.settings)
            sleep(5)
        printf("Syncer beendet.")
        self.isRunning = False


class ImageRefresher(Thread):
    def __init__(self, viewer):
        super(ImageRefresher, self).__init__()
        self.daemon = True
        self.viewer = viewer
        self.res = self.viewer.getXY()
        self.quit = False
        self.isRunning = False
        printf("ImageRefresher initialisiert.")

    def isNewRes(self):
        return self.res != self.viewer.getXY()

    def refreshRes(self):
        self.res = self.viewer.getXY()

    def quitThread(self):
        self.quit = True

    def run(self):
        self.isRunning = True
        printf("ImageRefresher gestartet.")
        while not self.quit:
            if self.isNewRes():
                LOCK.acquire()
                sleep(.1)
                self.refreshRes()
                self.viewer.displayImage()
                aRes = self.viewer.getActualRes()
                LOCK.release()
                printf("ImageRefresher: Auflösung des angezeigten Bildes angepasst auf "
                       "{0}x{1}.".format(aRes[0], aRes[1]))
            sleep(.1)
        printf("ImageRefresher beendet.")
        self.isRunning = False


class ImageLoader(Thread):
    def __init__(self, viewer, settings):
        super(ImageLoader, self).__init__()
        self.daemon = True
        self.viewer = viewer
        self.settings = settings
        self.quit = False
        self.isRunning = False
        printf("ImageLoader initialisiert.")

    def quitThread(self):
        self.quit = True

    def run(self):
        self.isRunning = True
        printf("ImageLoader gestartet.")
        while not self.quit:
            pics = Foto.alleLaden(orderBy="zeigDatum")
            end = datetime.today() + timedelta(seconds=self.settings.anzeigedauerSek)
            if pics:
                self.viewer.displayImage(pics[0].lokalPfad)
                pics[0].zeigDatum = datetime.today()
                pics[0].speichern()
                aRes = self.viewer.getActualRes()
                printf("ImageLoader: Bild wird angezeigt in {0}x{1}:\n\t{2}"
                       .format(aRes[0], aRes[1], pics[0].lokalPfad))
            else:
                printf("Keine Bilder zum Anzeigen vorhanden.")
            while (datetime.today() < end) and not self.quit:
                sleep(.01)
        printf("ImageLoader beendet.")
        self.isRunning = False


class ImageViewer(object):
    def __init__(self):
        self.tk = Tk()
        self.tk.geometry("600x400+10+10")
        self.tk.configure(background="black")
        self.isFullscreen = False
        self.tk.bind("<F11>", self.toggleFS)
        self.tk.bind("<Escape>", self.quitFS)
        self.tk.title("Fotobox Viewer")
        icon = PIL_Image.open(PATH + "fotobox.ico")
        self.icon = PIL_ImageTk.PhotoImage(icon)
        self.tk.tk.call("wm", "iconphoto", self.tk._w, self.icon)
        self.img = None
        self.imgLabel = None
        self.currentImagePath = None
        self.actualRes = (0, 0)
        printf("ImageViewer gestartet.")

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
        s = "Fullscreenmodus "
        if self.isFullscreen:
            s += "gestartet."
        else:
            s += "beendet."
        printf(s)

    def getGeometry(self):
        return self.tk.winfo_geometry()

    def getActualRes(self):
        return self.actualRes

    def getXY(self):
        strings = self.getGeometry().split("+")[0].split("x")
        return int(strings[0]), int(strings[1])

    def displayImage(self, localPath=None):
        try:
            if localPath is not None:
                self.currentImagePath = localPath

            if self.currentImagePath is not None:
                x, y = self.getXY()
                pic = PIL_Image.open(self.currentImagePath)
                ratio = min(float(x)/pic.size[0], float(y)/pic.size[1])
                pic = pic.resize((max(int(ratio*pic.size[0]), 1),
                                  max(int(ratio*pic.size[1]), 1)),
                                 PIL_Image.ANTIALIAS)
                self.actualRes = pic.size
                self.img = PIL_ImageTk.PhotoImage(pic)
                if self.imgLabel is not None:
                    self.imgLabel.destroy()
                self.imgLabel = Label(self.tk, image=self.img, background="black")
                self.imgLabel.pack()
        except RuntimeError as e:
            if "Too early to create image" in e.args:
                printf("RuntimeError in ImageViewer.displayImage ignoriert: Wahrscheinlich wurde das Programm "
                       "während der Anzeigeberechnung beendet. Es folgt eventuell ein AttributeError, "
                       "der ebenfalls ignoriert werden wird.")
        except IOError:
            printf("IOError beim Öffnen folgender Datei ignoriert (wurde wahrscheinlich zwischenzeitlich "
                   "gelöscht):\n\t{0}".format(self.currentImagePath))
        except Exception as e:
            printf("Unerwarteter Fehler in Methode ImageViewer.displayImage:\n{0}\n".format(e))
            raise


class Main(object):
    def __init__(self):
        if Einstellungen.get().init:
            desktop()
        try:
            SettingsWindow()
        except Exception as e:
            printf("Unerwarteter Fehler in SettingsWindow:\n{0}\n".format(e))
            raise
        self.settings = Einstellungen.get()
        Syncer.syncFotoDateien(self.settings)
        self.syncer = Syncer(self.settings)
        self.syncer.start()

        self.imageViewer = ImageViewer()
        self.imageLoader = ImageLoader(self.imageViewer, self.settings)
        self.imageRefresher = ImageRefresher(self.imageViewer)
        self.imageLoader.start()
        self.imageRefresher.start()
        self.imageViewer.tk.mainloop()

        self.syncer.quitThread()
        self.imageLoader.quitThread()
        self.imageRefresher.quitThread()
        end = datetime.today() + timedelta(seconds=5)
        while (not self.ready2quit()) and (datetime.today() < end):
            sleep(.01)
        if self.ready2quit():
            printf("Normales Programmende.")
            exit(0)
        else:
            printf("Beenden mindestens eines Threads dauerte länger als fünf Sekunden, Beenden erzwungen.")
            exit(2)

    def ready2quit(self):
        return not (self.syncer.isRunning or self.imageLoader.isRunning or self.imageRefresher.isRunning)


if __name__ == "__main__":
    if len(argv) == 1:
        try:
            mkdir(LOGPATH, 0o770)
        except OSError as e:
            if e.errno == EEXIST and isdir(LOGPATH):
                pass
            else:
                raise
        Main()
    elif len(argv) == 2:
        if argv[1] == "desktop":
            if desktop():
                exit(0)
            else:
                exit(1)
