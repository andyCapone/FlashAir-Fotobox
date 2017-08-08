# coding:utf-8

from Daten import Datentyp
from datetime import date, time, datetime
from subprocess import call
from os.path import basename, dirname, realpath
from os import stat
from shutil import copy2 as copy
from urllib2 import urlopen


class Einstellungen(Datentyp):
    SQLITE_TBL = "einstellungen"

    def standard(self):
        self.remoteOrdner = "/DCIM"
        self.lokalOrdner = dirname(realpath(__file__))
        self.anzeigedauerSek = 10
        self.downloadVerzoegerungMin = 0
        self.logging = True
        self.init = True
        self.verbindungsart = "Wifi"
        return self

    @staticmethod
    def get():
        einst = Einstellungen.alleLaden()
        if not einst:
            return Einstellungen().standard()
        return einst[0]

    def speichern(self, dbDatei=None):
        self.init = False
        super(Einstellungen, self).speichern(dbDatei)


class Foto(Datentyp):
    SQLITE_TBL = "fotos"
    IND_DIR = 0
    IND_NAM = 1
    IND_SIZ = 2
    IND_ATR = 3
    IND_DAT = 4
    IND_TIM = 5
    SUPPORTED = {"jpeg", "png", "bmp"}

    def getFoto(self, aufnDatum, size, remoteRoot, remotePfad, istRemote, lokalPfad=""):
        self.aufnDatum = aufnDatum
        self.zeigDatum = datetime(1900, 1, 1)
        self.size = size
        self.remotePfad = remoteRoot + remotePfad
        self.lokalPfad = lokalPfad
        self.istRemote = istRemote
        return self

    def download(self, dir, kind="wifi"):
        if self.istRemote:
            if not call(["mkdir", "-p", dir]):
                lokalPfad = self.__getLokalPfad(dir)
                tmp = lokalPfad.rsplit(".", 1)
                if len(tmp) == 1:
                    tmp.append("jpg")
                laufindex = 0
                while True:
                    try:
                        lokalPfad = "{0}_{1:03d}.{2}".format(tmp[0], laufindex, tmp[1])
                        open(lokalPfad).close()
                    except IOError:
                        break
                    else:
                        laufindex += 1
                try:
                    if kind == "wifi":
                        with open(lokalPfad, "wb") as f:
                            f.write(urlopen(self.remotePfad, timeout=5).read())
                    elif kind == "usb":
                        copy(self.remotePfad, lokalPfad)
                except:
                    return False
                else:
                    self.lokalPfad = lokalPfad
                    return True
        return False

    def getIdentifier(self):
        return "{0}_{1}".format(self.aufnDatum.strftime("%Y%m%d-%H%M%S"), self.remotePfad)

    def getRemoteOhneRoot(self, camUrl):
        return self.remotePfad.split(camUrl)[-1]

    @staticmethod
    def ladeOhneRemote():
        return Foto.bedingtLaden("remotePfad=?", "")

    @staticmethod
    def ladeAlleIdentifier():
        return {f.getIdentifier(): f.id for f in Foto.alleLaden()}

    @staticmethod
    def ladeRemote():
        return Foto.bedingtLaden("istRemote=?", "True")

    @staticmethod
    def ladeRemoteIdentifier():
        return [f.getIdentifier() for f in Foto.ladeRemote()]

    def __getLokalPfad(self, dir):
        while dir.endswith("/"):
            dir = dir[:-1]
        dir += "/"
        return dir + basename(self.remotePfad)

    @staticmethod
    def konvertiereRemote(raw, remoteRootPfad):
        l = raw.split(",")
        if int(l[Foto.IND_ATR]) != 0b100000:
            return None

        while remoteRootPfad.endswith("/"):
            remoteRootPfad = remoteRootPfad[:-1]
        remoteRootPfad += "/"
        while l[Foto.IND_DIR].startswith("/"):
            l[Foto.IND_DIR] = l[Foto.IND_DIR][1:]

        fotoPfad = l[Foto.IND_DIR] + "/" + l[Foto.IND_NAM]
        aufnDatum = Foto.konvDatum(int(l[Foto.IND_DAT]), int(l[Foto.IND_TIM]))
        size = int(l[Foto.IND_SIZ])
        return Foto().getFoto(aufnDatum, size, remoteRootPfad, fotoPfad, True)

    @staticmethod
    def konvertiereUSBRemote(remotePfad):
        s = stat(remotePfad)
        aufnDatum = datetime.utcfromtimestamp(s.st_ctime)
        size = int(s.st_size)
        return Foto().getFoto(aufnDatum, size, "", remotePfad, True)

    @staticmethod
    def konvertiereLokal(pfad):
        s = stat(pfad)
        aufnDatum = datetime.fromtimestamp(s.st_ctime)
        size = int(s.st_size)
        return Foto().getFoto(aufnDatum, size, "", "", False, pfad)

    @staticmethod
    def konvDatum(rawDatum, rawZeit):
        j = (rawDatum >> 9) + 1980
        m = (rawDatum >> 5) & 0xf
        t = rawDatum & 0x1f
        d = date(j, m, t)

        h = rawZeit >> 11
        m = (rawZeit >> 5) & 0x3f
        s = (rawZeit & 0x1f) * 2

        z = time(h, m, s)

        return datetime.combine(d, z)
