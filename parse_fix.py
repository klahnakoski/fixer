from collections import namedtuple

from bs4 import BeautifulSoup
from mo_dots import Data, listwrap, from_data, concat_field
from mo_files import File
from mo_future import first
from mo_kwargs import override
from mo_logs import Log

from XmlParser import XmlParser


class Fixer(object):
    def __init__(self):
        # LOAD THE XML FILE
        xml = File("spec/FIX42.xml").read()

        parsed = XmlParser().parse(xml)

        soup = BeautifulSoup(xml)

        fields = {}
        for t in first(c for c in parsed['children'] if c['name']=='fields')['children']:
            f = field(**t)
            fields[f.number] = f

        messages = {}
        for t in first(c for c in parsed['children'] if c['name'] == "messages")['children']:
            m = message(**t)
            messages[m.msgtype] = m

        # https: // en.wikipedia.org / wiki / Financial_Information_eXchange
        #                        0               1               2         3            4
        #                        0   12345   67890   123456   789012345678901234567   89012345   6789012   34567890
        data = "8=FIX.4.2\0019=45\00135=0\00134=3\00149=TW\00152=20000426-12:05:06\00156=ISLD\00110=218\001"
        char = 0
        for m in data.split("\001"):
            if not m:
                continue
            char += len(m)
            char += 1
            k, v = m.split("=")

            f = fields[k]

            if f.name == "BodyLength":
                body_end = char + int(v)
                body = data[char:body_end]
                checksum = sum(map(ord, data[:body_end])) % 256
            if f.name == "CheckSum":
                if checksum != int(v):
                    Log.error("checksum mismatch")
            if f.name == "MsgType":
                m = messages[v]
                if not hasattr(m, "type"):
                    setattr(m, "type", m.get_python_type())

                curr_message = m.get_python_type()



            if hasattr(f, 'enum'):
                v = f.enum[v]

            # SWITCH ON MESSAGE TYPE
            print(f.name + "=" + v)




class Base(object):
    @override
    def __init__(self, attributes=None, children=None):
        if attributes:
            self.__dict__ = attributes[0]
        if children:
            details = Data()
            for c in children:
                details[c['name']] += [globals()[c['name']](**c)]
            for k, v in details.items():
                setattr(self, k, from_data(listwrap(v)))




class fix(Base):
    pass


class header(Base):
    pass

class trailer(Base):
    pass


class message(Base):
    @override
    def __init__(self, attributes=None, children=None):
        if attributes:
            self.__dict__ = attributes

        self.fields = []
        self._add_group(".", children)
        self.python_type = namedtuple(self.name, (f.name for f in self.fields))

    def _add_group(self, name, children):
        for f in children:
            if f['name'] == "group":
                self._add_group(f['attributes']['name'], f['children'])
            else:
                f = field(**f)
                f.name = concat_field(name, f.name)
                self.fields.append(f)


class messages(Base):
    pass


class component(Base):
    pass

class components(Base):
    pass

class fields(Base):
    pass

class group(Base):
    pass


class field(object):
    @override
    def __init__(self, attributes=None, children=None):
        if attributes:
            self.__dict__ = attributes
        if children:
            self.enum = {
                c['attributes']['enum']: c['attributes']['description']
                for c in children
            }

    def __str__(self):
        return self.name


Fixer()