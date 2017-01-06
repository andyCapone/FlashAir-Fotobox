# coding:utf-8


from os import path
from datetime import datetime, date, time, timedelta
import sqlite3
from time import sleep
from json import JSONEncoder, JSONDecoder
import sys; reload(sys); sys.setdefaultencoding("utf-8")

DEBUG = False


class DB(object):
    VERSION = 3

    class Converter(object):
        # TODO alles static
        # TODO eigene Datentypen
        BUILT_IN = ["bool", "timedelta", "str", "int", "float", "datetime", "tuple", "list", "dict", "date", "time"]

        def konvertiere(self, data, typ=None):
            if typ is None:
                typ = DB.Converter.erkenneTyp(data)
            if typ in DB.Converter.BUILT_IN:
                m = getattr(self, typ)
                ret = m(data)
                if DEBUG:
                    print("Typ: {0}, Daten: {1}({2}), ret: {3}({4})".format(typ, data, DB.Converter.erkenneTyp(data), ret, DB.Converter.erkenneTyp(ret)))
                return ret
            else:
                # TODO Datentyp: id-methode bla, cls-name aus string -> getattr
                pass

        @staticmethod
        def erkenneTyp(data):
            return data.__class__.__name__

        @staticmethod
        def _raise(data, zielTyp):
            e = "Daten sind nicht vom Typ '{0}': {1}".format(zielTyp, data)
            raise ValueError(e)

        @staticmethod
        def str(data):
            return str(data)

        @staticmethod
        def bool(data):
            if isinstance(data, (str, unicode)):
                if data == "True":
                    return True
                return False
            elif isinstance(data, bool):
                return str(data)
            else:
                DB.Converter._raise(data, "bool")

        @staticmethod
        def int(data):
            if isinstance(data, (str, unicode)):
                return int(data)
            elif isinstance(data, int):
                return str(data)
            else:
                DB.Converter._raise(data, "int")

        @staticmethod
        def float(data):
            if isinstance(data, (str, unicode)):
                return float(data)
            elif isinstance(data, float):
                return str(data)
            else:
                DB.Converter._raise(data, "float")

        @staticmethod
        def datetime(data):
            if isinstance(data, datetime):
                return data.strftime(DB.DT_FORMAT)
            elif isinstance(data, (str, unicode)):
                return datetime.strptime(data, DB.DT_FORMAT)
            else:
                DB.Converter._raise(data, "datetime")

        @staticmethod
        def date(data):
            if isinstance(data, date):
                return data.strftime(DB.D_FORMAT)
            elif isinstance(data, (str, unicode)):
                return datetime.strptime(data, DB.D_FORMAT).date()
            else:
                DB.Converter._raise(data, "date")

        @staticmethod
        def time(data):
            if isinstance(data, time):
                return data.strftime(DB.T_FORMAT)
            elif isinstance(data, (str, unicode)):
                return datetime.strptime(data, DB.T_FORMAT).time()
            else:
                DB.Converter._raise(data, "time")

        @staticmethod
        def timedelta(data):
            if isinstance(data, timedelta):
                return str(data.total_seconds())
            elif isinstance(data, (str, unicode)):
                return timedelta(seconds=float(data))
            else:
                DB.Converter._raise(data, "timedelta")

        @staticmethod
        def dict(data):
            # TODO datentyp vom index beibehalten
            if isinstance(data, dict):
                d = {}
                for k in data.keys():
                    typ = DB.Converter.erkenneTyp(data[k])
                    d[k] = (DB.Converter().konvertiere(data[k], typ), typ)
                return str(JSONEncoder().encode(d))
            elif isinstance(data, (str, unicode)):
                d = JSONDecoder().decode(data)
                ret = {}
                for k in sorted(d.keys()):
                    ret[k] = DB.Converter().konvertiere(d[k][0], d[k][1])
                return ret
            else:
                DB.Converter._raise(data, "dict")

        @staticmethod
        def tuple(data):
            if isinstance(data, tuple):
                d = {}
                i = 0
                for dat in data:
                    typ = DB.Converter.erkenneTyp(dat)
                    d[i] = (DB.Converter().konvertiere(dat, typ), typ)
                    i += 1
                return str(JSONEncoder().encode(d))
            elif isinstance(data, (str, unicode)):
                d = JSONDecoder().decode(data)
                t = ()
                for k in sorted(d.keys()):
                    t = t + (DB.Converter().konvertiere(d[k][0], d[k][1]),)
                return t
            else:
                DB.Converter._raise(data, "tuple")

        @staticmethod
        def list(data):
            if isinstance(data, list):
                d = {}
                i = 0
                for dat in data:
                    typ = DB.Converter.erkenneTyp(dat)
                    d[i] = (DB.Converter().konvertiere(dat, typ), typ)
                    i += 1
                return str(JSONEncoder().encode(d))
            elif isinstance(data, (str, unicode)):
                d = JSONDecoder().decode(data)
                l = []
                for k in sorted(d.keys()):
                    l.append(DB.Converter().konvertiere(d[k][0], d[k][1]))
                return l
            else:
                DB.Converter._raise(data, "list")

    DATEI = path.dirname(path.realpath(__file__)) + "/db.sqlite"
    DT_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
    D_FORMAT = "%Y-%m-%d"
    T_FORMAT = "%H:%M:%S.%f"
    META_ERWEITERUNG = "METATAB"

    def execute(self, cursor, query, args=()):
        while True:
            try:
                if DEBUG:
                    print query
                    print(str(args) + "\n\n")
                ans = cursor.execute(query, args)
                break
            except sqlite3.OperationalError as e:
                if e.args:
                    if e.args[0] == "database is locked":
                        sleep(.01)
                    else:
                        raise
                else:
                    raise
        return ans

    def __init__(self, datei=None):
        if datei is None:
            datei = DB.DATEI
        if DEBUG:
            print "Datenbankpfad:", datei
        self.con = sqlite3.connect(datei)
        self.con.text_factory = str
        c = self.con.cursor()
        self.execute(c, "PRAGMA journal_mode = OFF")
        c.close()
        self.tblNamen = self.getTblNamen()

    def getTblNamen(self):
        c = self.con.cursor()
        ret = [t[0] for t in self.execute(c, "SELECT tbl_name FROM sqlite_master").fetchall()]
        c.close()
        return ret

    def getSpalten(self, tbl):
        c = self.con.cursor()
        roh = self.execute(c, "SELECT sql FROM sqlite_master WHERE tbl_name=?", (tbl,)).fetchone()
        c.close()
        if roh is None:
            return None
        return [s.split(" ")[0] for s in roh[0].split("(")[-1].split(")")[0].split(",")]

    def erstelleTabelle(self, obj):
        sAttr = sorted([a for a in obj.__dict__.keys() if a != "id"])
        q = "CREATE TABLE IF NOT EXISTS {0} (" \
            "_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL".format(obj.SQLITE_TBL)
        for a in sAttr:
            q += ",{0} TEXT".format(a)
        q += ")"
        cursor = self.con.cursor()
        self.execute(cursor, q)
        metatblName = obj.SQLITE_TBL + DB.META_ERWEITERUNG
        q = "CREATE TABLE IF NOT EXISTS {0} (spalte TEXT, typ TEXT)".format(metatblName)
        self.execute(cursor, q)
        for a in sAttr:
            q = "INSERT INTO {0} VALUES (?,?)".format(metatblName)
            self.execute(cursor, q, (a, DB.Converter.erkenneTyp(obj.__dict__[a])))
        cursor.close()

    def einfuegen(self, obj, cursor=None):
        tbl = obj.SQLITE_TBL
        if tbl not in self.tblNamen:
            if tbl is not None:
                self.erstelleTabelle(obj)
                self.tblNamen.append(tbl)
            else:
                s = "Es wurde kein {0}.SQLITE_TBL definiert.".format(obj.__class__.__name__)
                raise NotImplementedError(s)

        sAttr = sorted(obj.__dict__.keys())
        q = "INSERT INTO {0} VALUES (NULL".format(tbl) + (len(sAttr)-1)*",?" + ")"
        conv = DB.Converter()
        args = [conv.konvertiere(obj.__dict__[a]) for a in sAttr if a != "id"]

        if cursor is None:
            c = self.con.cursor()
        else:
            c = cursor
        self.execute(c, q, args)
        _id = c.lastrowid
        self.con.commit()
        if cursor is None:
            c.close()
        return _id

    def alleLaden(self, cls, cursor=None, orderBy=None, ascDesc="ASC", limit=None):
        if cursor is None:
            c = self.con.cursor()
        else:
            c = cursor

        q = "SELECT _id FROM {0}".format(cls.SQLITE_TBL)
        if orderBy is not None:
            q += " ORDER BY {0} {1}".format(orderBy, ascDesc)
        if limit is not None:
            q += " LIMIT {0}".format(limit)

        try:
            idTupel = self.execute(c, q).fetchall()
        except sqlite3.OperationalError:
            ret = []
        else:
            if idTupel is None:
                ret = []
            else:
                ret = [self.laden(cls, i[0], c) for i in idTupel]

        if cursor is None:
            c.close()
        return ret

    def bedingtLaden(self, cls, argStr, args, cursor=None):
        if not isinstance(args, tuple):
            args = (args,)
        q = "SELECT _id FROM {0} WHERE ".format(cls.SQLITE_TBL) + argStr
        if cursor is None:
            c = self.con.cursor()
        else:
            c = cursor
        try:
            idTupel = self.execute(c, q, args).fetchall()
        except sqlite3.OperationalError:
            ret = []
        else:
            if idTupel is None:
                ret = []
            else:
                ret = [self.laden(cls, i[0], c) for i in idTupel]

        if cursor is None:
            c.close()
        return ret

    def laden(self, cls, _id, cursor=None):
        if cursor is None:
            c = self.con.cursor()
        else:
            c = cursor

        q = "SELECT * FROM {0} WHERE _id=?".format(cls.SQLITE_TBL)
        try:
            roh = self.execute(c, q, (_id,)).fetchone()
        except sqlite3.OperationalError:
            roh = None

        if roh is None:
            if cursor is None:
                c.close()
            return None

        q = "SELECT * FROM {0}".format(cls.SQLITE_TBL + DB.META_ERWEITERUNG)
        typenTupelListe = self.execute(c, q).fetchall()
        typenDict = {t[0]: t[1] for t in typenTupelListe}

        conv = DB.Converter()
        l = self.getSpalten(cls.SQLITE_TBL)
        ret = cls(**{l[i]: conv.konvertiere(roh[i], typenDict[l[i]]) for i in range(len(l)) if l[i] != "_id"})
        ret.id = _id

        if cursor is None:
            c.close()
        return ret

    def update(self, obj, cursor=None):
        # TODO nur notwendige attribute updaten, vorher einmal laden und vergleichen
        if cursor is None:
            c = self.con.cursor()
        else:
            c = cursor

        q = "UPDATE {0} SET ".format(obj.SQLITE_TBL)
        conv = DB.Converter()
        sAttr = {k: conv.konvertiere(obj.__dict__[k]) for k in obj.__dict__.keys() if k != "id"}
        for k in sorted(sAttr.keys()):
            q += k + "=?,"
        q = q[:-1] + " WHERE _id=?"
        args = [sAttr[k] for k in sorted(sAttr.keys())]
        self.execute(c, q, args + [obj.__dict__["id"]])
        self.con.commit()

        if cursor is None:
            c.close()

    def loeschen(self, obj, cursor=None):
        if cursor is None:
            c = self.con.cursor()
        else:
            c = cursor

        q = "DELETE FROM {0} WHERE _id=?".format(obj.SQLITE_TBL)
        self.execute(c, q, (obj.id,))
        self.con.commit()

        if cursor is None:
            c.close()

    def leseLetzteId(self, cls, cursor=None):
        tbl = cls.SQLITE_TBL
        if tbl is None:
            s = "Es wurde kein {0}.SQLITE_TBL definiert.".format(cls.__name__)
            raise NotImplementedError(s)
        if cursor is None:
            c = self.con.cursor()
        else:
            c = cursor
        try:
            idTupel = self.execute(c, "SELECT seq FROM sqlite_sequence WHERE name=?", (cls.SQLITE_TBL,)).fetchone()
        except sqlite3.OperationalError as e:
            if e.args:
                if e.args[0].startswith("no such table"):
                    idTupel = None
                else:
                    raise
            else:
                raise

        if idTupel is None:
            _id = None
        else:
            _id = idTupel[0]

        if cursor is None:
            c.close()
        return _id


class Datentyp(object):
    SQLITE_TBL = None
    DB_DATEI = None

    def __init__(self, **kwargs):
        self.id = 0
        for key in kwargs.keys():
            self.__dict__[key] = kwargs[key]

    def speichern(self, dbDatei=None):
        if dbDatei is None:
            if self.DB_DATEI is None:
                dbDatei = DB.DATEI
            else:
                dbDatei = self.DB_DATEI

        if self.id == 0:
            self.id = DB(dbDatei).einfuegen(self)
        else:
            DB(dbDatei).update(self)

    def speichernUnter(self, dbDatei=None):
        if dbDatei is None:
            if self.DB_DATEI is None:
                dbDatei = DB.DATEI
            else:
                dbDatei = self.DB_DATEI

        self.id = DB(dbDatei).einfuegen(self)

    def loeschen(self, dbDatei=None):
        if dbDatei is None:
            if self.DB_DATEI is None:
                dbDatei = DB.DATEI
            else:
                dbDatei = self.DB_DATEI

        DB(dbDatei).loeschen(self)

    @classmethod
    def laden(cls, _id, dbDatei=None):
        if dbDatei is None:
            if cls.DB_DATEI is None:
                dbDatei = DB.DATEI
            else:
                dbDatei = cls.DB_DATEI

        return DB(dbDatei).laden(cls, _id)

    @classmethod
    def alleLaden(cls, dbDatei=None, orderBy=None, ascDesc="ASC", limit=None):
        if dbDatei is None:
            if cls.DB_DATEI is None:
                dbDatei = DB.DATEI
            else:
                dbDatei = cls.DB_DATEI

        return DB(dbDatei).alleLaden(cls, orderBy=orderBy, ascDesc=ascDesc, limit=limit)

    @classmethod
    def bedingtLaden(cls, argStr, args, dbDatei=None):
        if dbDatei is None:
            if cls.DB_DATEI is None:
                dbDatei = DB.DATEI
            else:
                dbDatei = cls.DB_DATEI

        return DB(dbDatei).bedingtLaden(cls, argStr, args)

    @classmethod
    def leseLetzteId(cls, dbDatei=None):
        if dbDatei is None:
            if cls.DB_DATEI is None:
                dbDatei = DB.DATEI
            else:
                dbDatei = cls.DB_DATEI

        return DB(dbDatei).leseLetzteId(cls)
