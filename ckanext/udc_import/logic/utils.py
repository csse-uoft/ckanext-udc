import csv
import io


def is_bom(buffer):
    f = io.TextIOWrapper(buffer, encoding='utf-8')
    chars = f.read(4)[0]
    f.close()
    return chars[0] == '\ufeff'


def read_csv(buffer, encoding=None):
    data = []
    if not encoding:
        encoding = 'utf-8-sig' if is_bom(buffer) else 'utf-8'
    with io.TextIOWrapper(buffer, encoding=encoding, newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            data.append(row)
    return data
