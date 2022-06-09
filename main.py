from settings import *
from book import *
from match import *

if __name__ == '__main__':
    book_en = Book.open_book('book3.epub', load=True, debug=False)
    book_zn = Book.open_book('book4.epub', load=True)

    book_en.get_translate()

    matcher = PageMatcher.open_matcher(book_en, book_zn, load=False)
    book_en, book_zn = matcher.get_books()
    matcher.match()
    aligner = Aligner()

    for page1, page2, _ in matcher.matched_pages[:]:
        page1.reset()
        if not page1.is_aligned:
            aligner.align(page1, page2)
            page1.print_page_combined()
    book_en.save_combined()
    print_time_log()
