import argparse

parser = argparse.ArgumentParser(description='manual to this script')
parser.add_argument('book', metavar='book', type=str, nargs='*', help='电子书所在文件，请放在epubs文件夹内',
                    default=['book1.epub', 'book2.epub'])
parser.add_argument('--preview', type=bool, default=True, help='是否打开预览功能，会在每个章节对齐后展示对齐内容')
parser.add_argument('--load', type=bool, default=True, help='是否加载本地保存的内容，继续执行任务，默认开启')

args = parser.parse_args()


if type(args.book) == list and len(args.book) > 2:
    # logger.warning("一次只能解析两本电子书。")
    exit()
elif len(args.book) < 2:
    # logger.warning("请同时输入中文与英文两本电子书。")
    exit()

book1, book2 = args.book
preview = args.preview
load = args.load
print(book1, book2, preview)
