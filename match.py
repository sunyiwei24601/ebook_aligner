# -*- coding: utf-8 -*-

from book import *
import pickle
from settings import *

# 文本相似度对比模型，在Comparator第一次使用时初始化
sim_model = None
TEMP_SAVE_DIR = "temp"

# 段落对齐相似度要求
ALIGN_THRESHOLD = 0.7
# 第一轮章节匹配度要求
PAGE_MATCH_FIRST_THRESHOLD = 0.8
# 第二轮章节匹配加入备选项要求
PAGE_MATCH_SECOND_THRESHOLD = 0.7


class Comparator:
    """
    文本相似度对比工具
    """

    def __init__(self):
        # 文本相似度对比缓存
        self.cache = {}

        # 初次使用时初始化
        global sim_model
        if sim_model is None:
            from text2vec import Similarity, EmbeddingType, SimilarityType
            sim_model = Similarity(model_name_or_path='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
            # from similarities.fastsim import HnswlibSimilarity 
            # sim_model = HnswlibSimilarity(
            # model_name_or_path='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

    def compare_sentence(self, sentence1, sentence2):
        """
        计算两个文本的相似度，返回-1 - 1之间， 1为最高，会使用Cache来缓存结果
        :param sentence1: 
        :param sentence2: 
        :return: 
        """
        if not self.cache.get((sentence1, sentence2)):
            score = sim_model.get_score(sentence1, sentence2)
            # score = sim_model.similarity(sentence1, sentence2)

            self.cache[(sentence1, sentence2)] = score
        return self.cache[(sentence1, sentence2)]


class Aligner:
    """
    段落对齐工具
    """

    def __init__(self):
        self.default_window_size = 2
        self.max_window_size = 10
        pass

    @time_log("Align_Pages")
    def align(self, page_left, page_right):
        """
        段落对齐的算法主体，page_left为英文段落，page_right为中文段落
        left 与 right 是滑动窗口的两个指针
        每次选择right指向的right_paragraph, 并维持一个以left指向的left_paragraph为中心构成的滑动窗口，与窗口内的文本进行相似度匹配
        找到匹配度足够高的段落就放到它的后面，表明匹配成功

        如果窗口内找不到匹配度足够高的段落，就把当前right_paragraph放入unassigned_paragraphs中，并扩大窗口大小，
        直到下次匹配成功时，一起放到left_paragraph后面

        如果持续找不到合适的匹配段落(window_size>20 超过10次)，则会启用兜底方案，遍历全文，为当前段落寻找匹配内容
        :param page_left: 英文章节
        :param page_right: 中文章节
        :return: 
        """
        logger.info("正在对齐章节 %s, %s", page_left.name, page_right.name)
        comparator = Comparator()
        left_paragraphs = page_left.paragraphs
        right_paragraphs = page_right.paragraphs

        # 剔除无效段落
        left_paragraphs = [_ for _ in left_paragraphs if len(_.text) > 1]
        right_paragraphs = [_ for _ in right_paragraphs if len(_.text) > 1]

        left_dict = {}
        for index, p in enumerate(left_paragraphs):
            left_dict[p] = index

        unassigned_paragraph = []

        left = 0  # 当前left_paragraph位置
        right = 0  # 当前right_paragraph位置
        stuck_times = 0  # 匹配卡住的次数

        with tqdm(total=len(right_paragraphs)) as bar:
            bar.set_description(f"正在对齐章节{page_left.name}的段落")
            while right < len(right_paragraphs) and left < len(left_paragraphs):
                is_match = False
                p_right = right_paragraphs[right]

                # 滑动窗口大小 = 默认窗口大小 + 堆积未分配的unassigned_paragraph的长度*2
                if stuck_times < 10:
                    window_size = min(self.default_window_size + 1 + len(unassigned_paragraph) * 2,
                                      self.max_window_size)
                else:  # 如果卡住超过 10 次，自动进入全文搜索阶段，window_size放到最大
                    window_size = int(len(left_paragraphs) / 2)
                potential_p_list = left_paragraphs[
                                   left: min(left + window_size, len(left_paragraphs))] + left_paragraphs[max(0,
                                                                                                              left - window_size): left]

                for i, p_left in enumerate(potential_p_list):
                    score = comparator.compare_sentence(p_left.text, p_right.text)
                    # 相似度超过threshold标记为匹配成功
                    if score >= ALIGN_THRESHOLD:
                        # 清空unassigned_paragraph, 和当前匹配到的段落放在一起
                        while len(unassigned_paragraph) > 0:
                            _ = unassigned_paragraph.pop()
                            left_paragraphs[max(0, left_dict[p_left] - 1)].add_subject(_)
                        # 把中文段落加到英文段落后面
                        p_left.add_subject(p_right, score)
                        right += 1
                        left = left_dict[p_left] + 1
                        is_match = True
                        stuck_times = 0
                        break

                if not is_match:
                    unassigned_paragraph.append(p_right)
                    right += 1
                    if window_size >= self.max_window_size:
                        stuck_times += 1
                    # 全文搜索之后仍然出现长时间卡住的情况，标记为 对齐出现了重大问题
                    if stuck_times > 20:
                        page_left.bad_aligned = True
                        logger.warning(f"章节{page1.name} - {page2.name} 段落对齐可能出现问题， 选择跳过该章节")
                        return

                bar.update(1)

        # 如果仍有剩余或未匹配成功的中文段落，全都加到最后
        if len(unassigned_paragraph) > 0:
            for _ in unassigned_paragraph:
                left_paragraphs[min(left, len(left_paragraphs) - 1)].add_subject(_)

        for _ in right_paragraphs[right:]:
            left_paragraphs[-1].add_subject(_)

        page_left.is_aligned = True
        page_left.save()


class PageMatcher:
    def __init__(self, book_left, book_right):
        self.pages_left = list(sorted(book_left.pages[:], key=lambda x: x.get_length(), reverse=True))
        self.pages_right = list(sorted(book_right.pages[:], key=lambda x: x.get_length(), reverse=True))
        self.book_length_left = book_left.get_length()
        self.book_length_right = book_right.get_length()
        self.filename = PageMatcher.get_filename(book_left, book_right)

        self.matched_pages = []
        self.unmatched_pages = self.pages_left[:]
        self.finished = False

    @time_log("Match_Pages")
    def match(self):
        """
        章节匹配算法的主体，left为英文版本，right为中文版，三轮匹配
        第一轮，根据left文本长度，选出合适的right备选章节，相似度>0.8直接返回
        第二轮，扩大备选章节数量，相似度大于0.8直接返回
        第三轮，如果以上两轮找不到的话，选择大于0.7且分数最高的章节作为匹配结果
        :return:
        """
        comparator = Comparator()

        if self.finished:
            return

        pages_left = self.unmatched_pages[:]
        matched_pages_candidates = []
        for page_left in pages_left:
            potential_pages = self.get_potential_pages(page_left)
            abstract_left = page_left.get_abstract(translated=True)
            is_match = False

            # 第一轮相似度大于0.8直接返回
            for page_right in potential_pages:
                abstract_right = page_right.get_abstract()
                score = comparator.compare_sentence(abstract_left, abstract_right)
                if score >= PAGE_MATCH_FIRST_THRESHOLD:
                    self.matched_pages.append((page_left, page_right, score))
                    self.pages_right.remove(page_right)
                    self.unmatched_pages.remove(page_left)
                    is_match = True
                    break

            # 第二轮，扩大搜索范围
            if not is_match:
                potential_pages = self.get_potential_pages(page_left, search_range=100)
                for page_right in potential_pages:
                    abstract_right = page_right.get_abstract(n=15)
                    score = comparator.compare_sentence(abstract_left, abstract_right)
                    # 相似度大于0.8直接返回
                    if score >= PAGE_MATCH_FIRST_THRESHOLD:
                        self.matched_pages.append((page_left, page_right, score))
                        self.pages_right.remove(page_right)
                        self.unmatched_pages.remove(page_left)
                        is_match = True
                        break
                    # 相似度 > 0.7 后放入备选列表
                    elif score >= PAGE_MATCH_SECOND_THRESHOLD:
                        matched_pages_candidates.append((page_left, page_right, score))

        # 第三轮，把备选列表按照分数进行排序，选出分数较高的部分
        matched_pages_candidates = sorted(matched_pages_candidates, key=lambda x: x[2], reverse=True)
        for page_left, page_right, score in matched_pages_candidates:
            if page_left in self.unmatched_pages and page_right in self.pages_right:
                self.matched_pages.append((page_left, page_right, score))
                self.pages_right.remove(page_right)
                self.unmatched_pages.remove(page_left)

        for page in self.unmatched_pages:
            logger.info("Matched Page not Found for page %s (body_end=%d): %s ", page.name, page.body_end,
                        page.get_abstract()[:50])
        self.save()
        self.finished = True

    def get_potential_pages(self, left_page, search_range=0.75):
        """
        根据英文章节的长度，选择长度接近的中文章节
        :param left_page: 英文章节
        :param search_range: 长度范围
        :return: [备选章节...]
        """
        left_page_percent = left_page.get_length() / self.book_length_left * 100
        right_page_percent_min = left_page_percent - search_range
        right_page_percent_max = left_page_percent + search_range
        potential_pages = []
        for page_right in self.pages_right:
            page_right_percent = page_right.get_length() / self.book_length_right * 100
            if right_page_percent_max > page_right_percent > right_page_percent_min:
                potential_pages.append(page_right)
        return potential_pages

    def save(self):
        with open(os.path.join(TEMP_SAVE_DIR, self.filename), 'wb') as f:
            pickle.dump(self, f)

    def get_books(self):
        """
        获取matcher当前正在匹配的两本书
        :return: book_en, book_zn
        """
        if len(self.matched_pages) > 0:
            return self.matched_pages[0][0].book, self.matched_pages[0][1].book
        else:
            return self.pages_left[0].book, self.pages_right[0].book

    def check_page_num(self):
        """
        匹配前检查一下两本书的主要章节数，如果相差过大，注意提醒用户注意电子书版本与质量
        :return: 
        """
        book_left, book_right = self.get_books()
        left_page_num, right_page_num = book_left.get_main_page_num(), book_right.get_main_page_num()
        gap = abs(left_page_num - right_page_num)

        # 章节数目差异超过某本书的一半，说明差异过大
        if gap < left_page_num / 2 and gap < right_page_num / 2:
            logger.info(f"{book_left.get_name()}主要章节数量:{left_page_num}, "
                        f"{book_right.get_name()[:20]}主要章节数量:{right_page_num},"
                        f" 数量大致匹配")
        else:
            logger.warning(f"{book_left.get_name()}主要章节数量:{left_page_num}, "
                           f"{book_right.get_name()[:20]}主要章节数量:{right_page_num},"
                           f"请检查电子书资源或者版本是否正确。")

    @staticmethod
    def get_filename(book_left, book_right):
        return book_left.get_name() + '_' + book_right.get_name() + '.match'

    @staticmethod
    def open_matcher(book1, book2, load=True):
        """
        读取或新建一个章节匹配器
        :param book1: 英文版
        :param book2: 中文版
        :param load: 是否加载已经保存的内容
        :return: 
        """
        filename = PageMatcher.get_filename(book1, book2)
        if filename in os.listdir(TEMP_SAVE_DIR) and load:
            with open(os.path.join(TEMP_SAVE_DIR, filename), 'rb') as f:
                return pickle.load(f)
        else:
            return PageMatcher(book1, book2)


if __name__ == '__main__':
    book1 = Book.open_book('book3.epub', load=True, translate=True)
    book2 = Book.open_book('book4.epub', load=True, translate=False)
    matcher = PageMatcher(book1, book2)
    matcher.match()

    matcher = PageMatcher.load('book3.match')
    aligner = Aligner()
    for page1, page2, _ in matcher.matched_pages:
        aligner.align(page1, page2)
        page1.print_page_combined()

    # book1 = matcher.pages_left[0].origin.book
    # book1.save('book3.epub')
