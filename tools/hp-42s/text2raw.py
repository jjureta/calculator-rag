import sys
import re
import os

if len(sys.argv) != 2:
    sys.exit("\ntxt2raw.pl V1.0 - Copyright 2005, Vini Matangrano\n"
             + "Special thanks to Thomas Okken for invaluable contribution\n\n"
             + "Usage: txt2raw.pl <filename>\n"
             + "A new file 'filename.raw' will be created.\n"
             + "\nNotes (aka \"Don't blame me, I warned you!\"):\n\n"
             + "1) There's not much error checking - use the script at your own risk.\n\n"
             + "2) Everything is CASE-SENSITIVE.\n\n"
             + "3) Keywords and parameters are distinguished by the spaces in between "
             + "them. I tried to follow HP-42S format as closely as possible. Please be "
             + "careful while typing - e.g., type\n\"STO+ ST Z\", don't type\n\"STO + "
             + "ST Z\", or \"STO+STZ\", or \"STO +STZ\", etc..\n\n"
             + "4) Weird characters. The following sequences will be translated into the "
             + "appropriate instructions:\n'x' (lowercase x) = multiplication (obs: "
             + "Free42's '×' is also supported),\n'/' = division (obs: Free42's '÷' is "
             + "also supported),\n"
             + "'|-' = concatenation character,\n'\\Sigma' = greek sigma "
             + "(statistics functions),\n'v' (lowercase v) = down arrow, as in \"Rv"
             + "\",\n'^' = up arrow,\n'<-' = left arrow,\n'->' = right arrow.\n\n"
             + "5) The substitutions above will only affect keywords, not the strings. "
             + "To enter special characters in strings, a txt2raw.prm file is provided, "
             + "and it can be edited to fit your needs.\n\n"
             + "6) Integer numbers at the beginning of lines that contain other words ("
             + "numeric or not) are interpreted as line numbers and therefore will be "
             + "ignored - this allows us to build programs from scratch without having to "
             + "type line numbers. If a '>' follows the number (as we see in program "
             + "listings before LBL instructions), it will be ignored as well.\n\n"
             + "7) I know, this is not state-of-the-art, but at least it's free...\n")

### My list of possible errors:
errors = [
    "No errors",
    "Keyword not found",
    "Bad parameters",
    "String too long"
]

### List of "fixed" opcodes
opcodes = {
    "CLX": "77",
    "ENTER": "83",
    "X<>Y": "71",
    "Rv": "75",
    "+/-": "54",
    "/": "43",
    "x": "42",
    "-": "41",
    "+": "40",
    "LASTX": "76",
    "SIN": "59",
    "COS": "5A",
    "TAN": "5B",
    "ASIN": "5C",
    "ACOS": "5D",
    "ATAN": "5E",
    "LOG": "56",
    "10^X": "57",
    "LN": "50",
    "E^X": "55",
    "SQRT": "52",
    "X^2": "51",
    "1/X": "60",
    "Y^X": "53",
    "%": "4C",
    "PI": "72",
    "COMPLEX": "A0 72",
    "ALL": "A2 5D",
    "NULL": "00",
    "CLA": "87",
    "DEG": "80",
    "RAD": "81",
    "GRAD": "82",
    "RECT": "A2 5A",
    "POLAR": "A2 59",
    "CPXRES": "A2 6A",
    "REALRES": "A2 6B",
    "KEYASN": "A2 63",
    "LCLBL": "A2 64",
    "RDX.": "A2 5B",
    "RDX,": "A2 5C",
    "CL\\Sigma": "70",
    "CLST": "73",
    "CLRG": "8A",
    "CLKEYS": "A2 62",
    "CLLCD": "A7 63",
    "CLMENU": "A2 6D",
    "->DEG": "6B",
    "->RAD": "6A",
    "->HR": "6D",
    "->HMS": "6C",
    "->REC": "4E",
    "->POL": "4F",
    "IP": "68",
    "FP": "69",
    "RND": "6E",
    "ABS": "61",
    "SIGN": "7A",
    "MOD": "4B",
    "COMB": "A0 6F",
    "PERM": "A0 70",
    "N!": "62",
    "GAMMA": "A0 74",
    "RAN": "A0 71",
    "SEED": "A0 73",
    "RTN": "85",
    "AVIEW": "7E",
    "PROMPT": "8E",
    "PSE": "89",
    "AIP": "A6 31",
    "XTOA": "A6 6F",
    "AGRAPH": "A7 64",
    "PIXEL": "A7 65",
    "BEEP": "86",
    "GETKEY": "A2 6E",
    "MENU": "A2 5E",
    "X=0?": "67",
    "X!=0?": "63",
    "X<0?": "66",
    "X>0?": "64",
    "X<=0?": "7B",
    "X>=0?": "A2 5F",
    "X=Y?": "78",
    "X!=Y?": "79",
    "X<Y?": "44",
    "X>Y?": "45",
    "X<=Y?": "46",
    "X>=Y?": "A2 60",
    "PR\\Sigma": "A7 52",
    "PRSTK": "A7 53",
    "PRA": "A7 48",
    "PRX": "A7 54",
    "PRUSR": "A7 61",
    "ADV": "8F",
    "PRLCD": "A7 62",
    "DELAY": "A7 60",
    "PRON": "A7 5E",
    "PROFF": "A7 5F",
    "MAN": "A7 5B",
    "NORM": "A7 5C",
    "TRACE": "A7 5D",
    "\\Sigma+": "47",
    "\\Sigma-": "48",
    "END": "C0 00 0D",
    ".END.": "C0 00 0D",
    "STOP": "84",
    "NEWMAT": "A6 DA",
    "R^": "74",
    "REAL?": "A2 65",
    "CPX?": "A2 67",
    "STR?": "A2 68",
    "MAT?": "A2 66",
    "DIM?": "A6 E7",
    "ON": "A2 70",
    "OFF": "8D",
    "\\SigmaREG?": "A6 78",
    "CLD": "7F",
    "ACOSH": "A0 66",
    "ALENG": "A6 41",
    "ALL\\Sigma": "A0 AE",
    "AND": "A5 88",
    "AOFF": "8B",
    "AON": "8C",
    "AROT": "A6 46",
    "ASHF": "88",
    "ASINH": "A0 64",
    "ATANH": "A0 65",
    "ATOX": "A6 47",
    "BASE+": "A0 E6",
    "BASE-": "A0 E7",
    "BASEx": "A0 E8",
    "BASE/": "A0 E9",
    "BASE+/-": "A0 EA",
    "BEST": "A0 9F",
    "BINM": "A0 E5",
    "BIT?": "A5 8C",
    "CORR": "A0 A7",
    "COSH": "A0 62",
    "CROSS": "A6 CA",
    "CUSTOM": "A2 6F",
    "DECM": "A0 E3",
    "DELR": "A0 AB",
    "DET": "A6 CC",
    "DOT": "A6 CB",
    "EDIT": "A6 E1",
    "EXITALL": "A2 6C",
    "EXPF": "A0 A0",
    "E^X-1": "58",
    "FCSTX": "A0 A8",
    "FCSTY": "A0 A9",
    "FNRM": "A6 CF",
    "GETM": "A6 E8",
    "GROW": "A6 E3",
    "HEXM": "A0 E2",
    "HMS+": "49",
    "HMS-": "4A",
    "I+": "A6 D2",
    "I-": "A6 D3",
    "INSR": "A0 AA",
    "INVRT": "A6 CE",
    "J+": "A6 D4",
    "J-": "A6 D5",
    "LINF": "A0 A1",
    "LIN\\Sigma": "A0 AD",
    "LN1+X": "65",
    "LOGF": "A0 A2",
    "MEAN": "7C",
    "NOT": "A5 87",
    "OCTM": "A0 E4",
    "OLD": "A6 DB",
    "OR": "A5 89",
    "POSA": "A6 5C",
    "PUTM": "A6 E9",
    "PWRF": "A0 A3",
    "RCLEL": "A6 D7",
    "RCLIJ": "A6 D9",
    "RNRM": "A6 ED",
    "ROTXY": "A5 8B",
    "RSUM": "A6 D0",
    "R<>R": "A6 D1",
    "SDEV": "7D",
    "SINH": "A0 61",
    "SLOPE": "A0 A4",
    "STOEL": "A6 D6",
    "STOIJ": "A6 D8",
    "SUM": "A0 A5",
    "TANH": "A0 63",
    "TRANS": "A6 C9",
    "UVEC": "A6 CD",
    "WMEAN": "A0 AC",
    "WRAP": "A6 E2",
    "XOR": "A5 8A",
    "YINT": "A0 A6",
    "->DEC": "5F",
    "->OCT": "6F",
    "<-": "A6 DC",
    "^": "A6 DE",
    "v": "A6 DF",
    "->": "A6 DD",
    "%CH": "4D",
    "`str`": "Fn",
    "[MAX]": "A6 EB",
    "[MIN]": "A6 EA",
    "[FIND]": "A6 EC"
}

### List of "modifiable" opcodes
modified = {
    "STO": {
        "sr": "3r",
        "rr": "91 rr",
        "ST": "91 7t",
        "`str`": "Fn 81",
        "IND sr": "91 8r",
        "IND rr": "91 8r",
        "IND ST": "91 Ft",
        "IND `str`": "Fn 89"
    },
    "STO+": {
        "sr": "92 rr",
        "rr": "92 rr",
        "ST": "92 7t",
        "`str`": "Fn 82",
        "IND sr": "92 8r",
        "IND rr": "92 8r",
        "IND ST": "92 Ft",
        "IND `str`": "Fn 8A"
    },
    "STO-": {
        "sr": "93 rr",
        "rr": "93 rr",
        "ST": "93 7t",
        "`str`": "Fn 83",
        "IND sr": "93 8r",
        "IND rr": "93 8r",
        "IND ST": "93 Ft",
        "IND `str`": "Fn 8B"
    },
    "STOx": {
        "sr": "94 rr",
        "rr": "94 rr",
        "ST": "94 7t",
        "`str`": "Fn 84",
        "IND sr": "94 8r",
        "IND rr": "94 8r",
        "IND ST": "94 Ft",
        "IND `str`": "Fn 8C"
    },
    "STO/": {
        "sr": "95 rr",
        "rr": "95 rr",
        "ST": "95 7t",
        "`str`": "Fn 85",
        "IND sr": "95 8r",
        "IND rr": "95 8r",
        "IND ST": "95 Ft",
        "IND `str`": "Fn 8D"
    },
    "RCL": {
        "sr": "2r",
        "rr": "90 rr",
        "ST": "90 7t",
        "`str`": "Fn 91",
        "IND sr": "90 8r",
        "IND rr": "90 8r",
        "IND ST": "90 Ft",
        "IND `str`": "Fn 99"
    },
    "RCL+": {
        "sr": "F2 D1 rr",
        "rr": "F2 D1 rr",
        "ST": "F2 D1 7t",
        "`str`": "Fn 92",
        "IND sr": "F2 D1 8r",
        "IND rr": "F2 D1 8r",
        "IND ST": "F2 D1 Ft",
        "IND `str`": "Fn 9A"
    },
    "RCL-": {
        "sr": "F2 D2 rr",
        "rr": "F2 D2 rr",
        "ST": "F2 D2 7t",
        "`str`": "Fn 93",
        "IND sr": "F2 D2 8r",
        "IND rr": "F2 D2 8r",
        "IND ST": "F2 D2 Ft",
        "IND `str`": "Fn 9B"
    },
    "RCLx": {
        "sr": "F2 D3 rr",
        "rr": "F2 D3 rr",
        "ST": "F2 D3 7t",
        "`str`": "Fn 94",
        "IND sr": "F2 D3 8r",
        "IND rr": "F2 D3 8r",
        "IND ST": "F2 D3 Ft",
        "IND `str`": "Fn 9C"
    },
    "RCL/": {
        "sr": "F2 D4 rr",
        "rr": "F2 D4 rr",
        "ST": "F2 D4 7t",
        "`str`": "Fn 95",
        "IND sr": "F2 D4 8r",
        "IND rr": "F2 D4 8r",
        "IND ST": "F2 D4 Ft",
        "IND `str`": "Fn 9D"
    },
    "LBL": {
        "sl": "0l",
        "ll": "CF nn",
        "xl": "CF xx",
        "`str`": "C0 00 Fn 00"
    },
    "GTO": {
        "sl": "Bl 00",
        "ll": "D0 00 nn",
        "xl": "D0 00 xx",
        "`str`": "1D Fn",
        "IND sl": "AE nn",
        "IND ll": "AE nn",
        "IND ST": "AE 7t",
        "IND `str`": "Fn AE"
    },
    "XEQ": {
        "sl": "E0 00 nn",
        "ll": "E0 00 nn",
        "xl": "E0 00 xx",
        "`str`": "1E Fn",
        "IND sl": "AE 8r",
        "IND ll": "AE 8r",
        "IND ST": "AE Ft",
        "IND `str`": "Fn AF"
    },
    "ASTO": {
        "sr": "9A rr",
        "rr": "9A rr",
        "ST": "9A 7t",
        "`str`": "Fn B2",
        "IND sr": "9A 8r",
        "IND rr": "9A 8r",
        "IND ST": "9A Ft",
        "IND `str`": "Fn BA"
    },
    "ARCL": {
        "sr": "9B rr",
        "rr": "9B rr",
        "ST": "9B 7t",
        "`str`": "Fn B3",
        "IND sr": "9B 8r",
        "IND rr": "9B 8r",
        "IND ST": "9B Ft",
        "IND `str`": "Fn BB"
    },
    "FIX": {
        "sd": "9C nn",
        "10": "F1 D5",
        "11": "F1 E5",
        "IND rr": "9C 8r",
        "IND ST": "9C Ft",
        "IND `str`": "Fn DC"
    },
    "SCI": {
        "sd": "9D nn",
        "10": "F1 D6",
        "11": "F1 E6",
        "IND rr": "9D 8r",
        "IND ST": "9D Ft",
        "IND `str`": "Fn DD"
    },
    "ENG": {
        "sd": "9E nn",
        "10": "F1 D7",
        "11": "F1 E7",
        "IND rr": "9E 8r",
        "IND ST": "9E Ft",
        "IND `str`": "Fn DE"
    },
    "ISG": {
        "sr": "96 rr",
        "rr": "96 rr",
        "ST": "96 7t",
        "`str`": "Fn 96",
        "IND sr": "96 8r",
        "IND rr": "96 8r",
        "IND ST": "96 Ft",
        "IND `str`": "Fn 9E"
    },
    "DSE": {
        "sr": "97 rr",
        "rr": "97 rr",
        "ST": "97 7t",
        "`str`": "Fn 97",
        "IND sr": "97 8r",
        "IND rr": "97 8r",
        "IND ST": "97 Ft",
        "IND `str`": "Fn 9F"
    },
    "KEY `key` GTO": {
        "sl": "F3 E3 kk rr",
        "ll": "F3 E3 kk rr",
        "xl": "F3 E3 kk xx",
        "`str`": "Fn C3 kk",
        "IND sl": "F3 E3 kk 8r",
        "IND ll": "F3 E3 kk 8r",
        "IND ST": "F3 E3 kk Ft",
        "IND `str`": "Fn CB kk"
    },
    "KEY `key` XEQ": {
        "sl": "F3 E2 kk rr",
        "ll": "F3 E2 kk rr",
        "xl": "F3 E2 kk xx",
        "`str`": "Fn C2 kk",
        "IND sl": "F3 E2 kk 8r",
        "IND ll": "F3 E2 kk 8r",
        "IND ST": "F3 E2 kk Ft",
        "IND `str`": "Fn CA kk"
    },
    "DIM": {
        "`str`": "Fn C4",
        "IND sr": "F2 EC 8r",
        "IND rr": "F2 EC 8r",
        "IND ST": "F2 EC Ft",
        "IND `str`": "Fn CC"
    },
    "EDITN": {
        "`str`": "Fn C6",
        "IND sr": "F2 EF 8r",
        "IND rr": "F2 EF 8r",
        "IND ST": "F2 EF Ft",
        "IND `str`": "Fn CE"
    },
    "INDEX": {
        "`str`": "Fn 87",
        "IND sr": "F2 DA 8r",
        "IND rr": "F2 DA 8r",
        "IND ST": "F2 DA Ft",
        "IND `str`": "Fn 8F"
    },
    "X<>": {
        "sr": "CE rr",
        "rr": "CE rr",
        "ST": "CE 7t",
        "`str`": "Fn 86",
        "IND sr": "CE 8r",
        "IND rr": "CE 8r",
        "IND ST": "CE Ft",
        "IND `str`": "Fn 8E"
    },
    "SF": {
        "sr": "A8 rr",
        "rr": "A8 rr",
        "IND sr": "A8 8r",
        "IND rr": "A8 8r",
        "IND ST": "A8 Ft",
        "IND `str`": "Fn A8"
    },
    "CF": {
        "sr": "A9 rr",
        "rr": "A9 rr",
        "IND sr": "A9 8r",
        "IND rr": "A9 8r",
        "IND ST": "A9 Ft",
        "IND `str`": "Fn A9"
    },
    "FS?": {
        "sr": "AC rr",
        "rr": "AC rr",
        "IND sr": "AC 8r",
        "IND rr": "AC 8r",
        "IND ST": "AC Ft",
        "IND `str`": "Fn AC"
    },
    "FC?": {
        "sr": "AD rr",
        "rr": "AD rr",
        "IND sr": "AD 8r",
        "IND rr": "AD 8r",
        "IND ST": "AD Ft",
        "IND `str`": "Fn AD"
    },
    "FS?C": {
        "sr": "AA rr",
        "rr": "AA rr",
        "IND sr": "AA 8r",
        "IND rr": "AA 8r",
        "IND ST": "AA Ft",
        "IND `str`": "Fn AA"
    },
    "FC?C": {
        "sr": "AB rr",
        "rr": "AB rr",
        "IND sr": "AB 8r",
        "IND rr": "AB 8r",
        "IND ST": "AB Ft",
        "IND `str`": "Fn AB"
    },
    "VIEW": {
        "sr": "98 rr",
        "rr": "98 rr",
        "ST": "98 7t",
        "`str`": "Fn 80",
        "IND sr": "98 8r",
        "IND rr": "98 8r",
        "IND ST": "98 Ft",
        "IND `str`": "Fn 88"
    },
    "INPUT": {
        "sr": "F2 D0 rr",
        "rr": "F2 D0 rr",
        "ST": "F2 D0 7t",
        "`str`": "Fn C5",
        "IND sr": "F2 EE 8r",
        "IND rr": "F2 EE 8r",
        "IND ST": "F2 EE Ft",
        "IND `str`": "Fn CD"
    },
    "CLV": {
        "`str`": "Fn B0",
        "IND sr": "F2 D8 8r",
        "IND rr": "F2 D8 8r",
        "IND ST": "F2 D8 Ft",
        "IND `str`": "Fn B8"
    },
    "CLP": {
        "`str`": "Fn F0"
    },
    "TONE": {
        "sr": "9F rr",
        "rr": "9F rr",
        "IND sr": "9F 8r",
        "IND rr": "9F 8r",
        "IND ST": "9F Ft",
        "IND `str`": "Fn DF"
    },
    "MVAR": {
        "`str`": "Fn 90"
    },
    "VARMENU": {
        "`str`": "Fn C1",
        "IND sr": "F2 F8 8r",
        "IND rr": "F2 F8 8r",
        "IND ST": "F2 F8 Ft",
        "IND `str`": "Fn C9"
    },
    "PRV": {
        "`str`": "Fn B1",
        "IND sr": "F2 D9 8r",
        "IND rr": "F2 D9 8r",
        "IND ST": "F2 D9 Ft",
        "IND `str`": "Fn B9"
    },
    "\\SigmaREG": {
        "sr": "99 rr",
        "rr": "99 rr",
        "IND sr": "99 8r",
        "IND rr": "99 8r",
        "IND ST": "99 Ft",
        "IND `str`": "Fn DB"
    },
    "INTEG": {
        "`str`": "Fn B6",
        "IND sr": "F2 EA 8r",
        "IND rr": "F2 EA 8r",
        "IND ST": "F2 EA Ft",
        "IND `str`": "Fn BE"
    },
    "PGMSLV": {
        "`str`": "Fn B5",
        "IND sr": "F2 E9 8r",
        "IND rr": "F2 E9 8r",
        "IND ST": "F2 E9 Ft",
        "IND `str`": "Fn BD"
    },
    "PGMINT": {
        "`str`": "Fn B4",
        "IND sr": "F2 E8 8r",
        "IND rr": "F2 E8 8r",
        "IND ST": "F2 E8 Ft",
        "IND `str`": "Fn BC"
    },
    "SOLVE": {
        "`str`": "Fn B7",
        "IND sr": "F2 EB 8r",
        "IND rr": "F2 EB 8r",
        "IND ST": "F2 EB Ft",
        "IND `str`": "Fn BF"
    },
    "ASSIGN": {
        "`str`": "Fn C0 aa"
    },
    "SIZE": {
        "sr": "F3 F7 ww ww",
        "rr": "F3 F7 ww ww"
    },
    "|-": {
        "`str`": "Fn 7F"
    }
}

### "Values" of stack registers
stack = {
    "T": 0,
    "Z": 1,
    "Y": 2,
    "X": 3,
    "L": 4
}


### Changing integers into hex string (one single byte).
def hxa(byte):
    byte = int(byte)
    aux = byte % 16
    hx = chr(48 + aux + (7 if aux > 9 else 0))
    byte = byte // 16
    aux = byte % 16
    hx = chr(48 + aux + (7 if aux > 9 else 0)) + hx
    return hx


### Changing strings into corresponding opcodes (also adjusting the
### instruction length in "Fn" byte). Special characters will be 
### translated as defined in txt2raw.prm file.
def string_proc(aux, str_val):
    global error, special
    length_str = len(str_val)
    pos = aux.find("Fn")
    
    str_content = str_val[1:-1]
    for s_pair in special:
        pattern = re.escape(s_pair[0])
        replacement = chr(int(s_pair[1]))
        str_content = str_content.replace(s_pair[0], replacement)
        
    length_str = len(str_content)
    limit = 14 if aux == "Fn 7F" else (15 if aux == "Fn" else 7)
    if length_str > limit:
        error = 3
        return None

    for i in range(length_str):
        aux += " " + hxa(ord(str_content[i]))

    aux = re.sub(r' aa(.*)', r'\1 nn', aux)

    dist = (len(aux) - pos - 2) // 3
    aux = aux[:pos] + hxa(240 + dist) + aux[pos + 2:]

    return aux


### Parameter processing.
def process(opc, line_idx, words):
    global error, strings, keys, modified, stack
    num = 0

    auxh = modified[opc]
    key = ""

    if words and words[0] == "IND":
        key += ("" if key == "" else " ") + words.pop(0)

    if words and words[0] == "ST":
        key += ("" if key == "" else " ") + words.pop(0)

    if words and words[0] == "`str`":
        key += ("" if key == "" else " ") + words.pop(0)

    if words and words[0] == "TO":
        words.pop(0)
        num = int(words.pop(0)) - 1

    if words and re.match(r'^\d+$', words[0]):
        num = int(words.pop(0))
        if re.search(r'(LBL|GTO|XEQ)', opc):
            key += ("" if key == "" else " ") + ("sl" if num < 15 else "ll")
        else:
            if re.search(r'(FIX|SCI|ENG)', opc):
                key += " rr" if key == "IND" else ("sd" if num < 10 else str(num))
            else:
                key += (" " if key == "IND" else "") + ("sr" if num < 16 else "rr")

    if words and re.match(r'^[A-J]$', words[0], re.IGNORECASE):
        key = "xl"
        num = ord(words.pop(0).upper()) + 37
        if num > 133:
            num -= 11

    if words and words[0] in "LXYZT":
        num = stack[words.pop(0)]
   
    if key not in auxh:
        return None
    aux = auxh[key]

    if "`str`" in key:
        aux = string_proc(aux, strings[line_idx])

    if aux is None: return None

    aux = re.sub(r'ww ww', lambda m: hxa(num // 256) + " " + hxa(num % 256), aux)
    aux = re.sub(r'll', lambda m: "CF " + hxa(num), aux)
    aux = re.sub(r'([\dA-F])l', lambda m: hxa(int(m.group(1) + "0", 16) + 1 + num), aux)
    aux = re.sub(r'xx', lambda m: hxa(num), aux)
    aux = re.sub(r'rr', lambda m: hxa(num), aux)
    aux = re.sub(r'nn', lambda m: hxa(num), aux)
    aux = re.sub(r'(\d)r', lambda m: hxa(int(m.group(1)) * 16 + num), aux)
    aux = re.sub(r'([\dA-F])t', lambda m: m.group(1) + str(num), aux)
    aux = re.sub(r'kk', lambda m: hxa(keys[line_idx]), aux)

    return aux


### Changing numbers into corresponding opcodes.
def number_proc(num):
    num = re.sub(r'(\d)', r' 1\1', num)
    num = num.replace('.', ' 1A')
    num = num.replace('E', ' 1B')
    num = num.replace('-', ' 1C')
    num = num.replace(' ', '')
    num += " 00"
    return num


### Sending binary data to output file.
def outp(str_val):
    global outf
    for byte_str in str_val.split():
        outf.write(bytes([int(byte_str, 16)]))


### Opening input and output files
try:
    file_in = open(sys.argv[1], 'r')
except:
    sys.exit("Damn! Can't open file!\n")

file_out_name = sys.argv[1] + ".raw"
outf = open(file_out_name, 'wb')

special = []
if os.path.exists("txt2raw.prm"):
    with open("txt2raw.prm", 'r') as prm_f:
        for line in prm_f:
            if re.match(r'^\s*$', line): continue
            if line.startswith('#'): continue
            line = re.sub(r'\\(\d{3})', lambda m: chr(int(m.group(1))), line)
            line = line.replace('\\', '\\\\')
            line = line.lstrip()
            line = line.rstrip('\n')
            special.append(line.split())

error = 0
line_count = 0
strings = {}
keys = {}

### Main loop
for line in file_in:
    if error != 0: break
    line_count += 1
    if not re.search(r'[\w\"\-\+\/×÷%]', line): continue
    if re.search(r'\{ \d+\-Byte Prgm \}', line): continue
    sys.stdout.write(line)
    line = line.rstrip('\n')

    ### Strings will be temporarily replaced with a special token
    if re.search(r'\".*\"', line):
        m = re.search(r'\".*\"', line)
        strings[line_count] = m.group(0)
        line = re.sub(r'(\".*\")', ' `str` ', line)

    ### Same for keys
    if re.search(r'KEY\s+(\d) ', line):
        m = re.search(r'KEY\s+(\d) ', line)
        keys[line_count] = m.group(1)
        line = re.sub(r'KEY\s+\d ', 'KEY `key` ', line)

    line = line.strip()

    ### Split up the code line, ignore line numbers if any
    words = line.split()
    if len(words) > 1 and re.match(r'^\d+$', words[0]):
        words.pop(0)

    if not words: continue
    opc = words.pop(0)

    ### Do we have a string?
    if opc == "`str`":
        aux = string_proc(opcodes[opc], strings[line_count])
        outp(aux)
        continue

    ### This is for compatibility with Free42 print-out feature
    opc = re.sub(r'^\d+\>', '', opc)
    opc = opc.replace('×', 'x')
    opc = opc.replace('÷', '/')

    ### Do we have a number?
    if re.match(r'^\-?\d+(\.\d+|)(E\-?\d{1,3}|)$', opc):
        res = number_proc(opc)
        outp(res)
        continue

    ### Do we have a "fixed" opcode? If so, go ahead and spit it out
    if opc in opcodes:
        outp(opcodes[opc])
        continue

    ### Do we have a KEY... GTO/XEQ instruction?
    if words and words[0] == "`key`":
        opc += " " + words.pop(0)
        opc += " " + words.pop(0)

    ### Do we have a "modifiable" opcode? If so, process parameters before spitting
    if opc in modified:
        aux = process(opc, line_count, words)
        if aux is None:
            if error == 0: error = 2
            break
        outp(aux)
        continue

    ### If everything above failed, all we can do now is cry...
    error = 1

file_in.close()
outf.close()

if error:
    opc = opc.replace('`str`', strings.get(line_count, ''))
    sys.exit(f"Error: {errors[error]}!\nLine {line_count} ('{opc}').\nAborting...\n")

print(f"{errors[error]}.")
