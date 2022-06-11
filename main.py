from settings import *
from book import *
from match import *
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='manual to this script')
    parser.add_argument('book', metavar='book', type=str, nargs='*', help='电子书所在文件，请放在epubs文件夹内',
                        default=['book1.epub', 'book2.epub'])
    parser.add_argument('--preview', type=bool, default=True, help='是否打开预览功能，会在每个章节对齐后展示对齐内容, 默认开启')
    parser.add_argument('--load', type=bool, default=True, help='是否加载本地保存的内容，继续执行任务，默认开启')

    args = parser.parse_args()

    if type(args.book) == list and len(args.book) > 2:
        logger.warning("一次只能解析两本电子书。")
        exit()
    elif len(args.book) < 2:
        logger.warning("请同时输入中文与英文两本电子书。")
        exit()

    book1, book2 = args.book
    preview = args.preview
    load = args.load

    book_en = Book.open_book(book1, load=load, debug=False)
    book_zn = Book.open_book(book2, load=load)

    book_en.get_translate()

    matcher = PageMatcher.open_matcher(book_en, book_zn, load=load)
    matcher.check_page_num()
    book_en, book_zn = matcher.get_books()
    matcher.match()
    aligner = Aligner()

    for page1, page2, _ in matcher.matched_pages[:]:
        # page1.reset()
        if not page1.is_aligned:
            aligner.align(page1, page2)
            if preview:
                page1.print_page_combined()
    book_en.save_combined()
    print_time_log()
