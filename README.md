# E-Book Aligner 跨语言电子书对齐
## 介绍

作为非英语母语使用者，每次阅读原版英文书，都会让我有一种自己是文盲的既视感。 阅读器自带单词翻译无法通顺理解原文，而机器翻译整句句子，一来操作繁琐，二来很难兼顾信达雅，或有曲解。

同时，很多书其实都有它的中文译本，我也曾试过开两个屏幕，对照阅读，体验上也不太好（转来转去真的对颈椎伤害很大:joy:),所以为了方便，也自娱自乐一下，开发了这款程序。

简单来说实现的功能就是，将两本已经找到的epub电子书（中文与英文版本），合并为一本电子书，其中新生成的电子书会以一段英文+一段中文的形式交替呈现，如下所示：

```tex
# 英文版本
I AM SHY. In elementary school for a play about a safari, everyone else was an animal. I was grass. I’ve never asked a question in a large lecture hall. 

I’ll apologize if you bump into me. I’ll accept every pamphlet you hand out on the street. I’ve always rolled my shopping cart back to its place of origin. If there’s no more half-and-half on the counter at the coffee shop, I’ll drink my coffee black. If I sleep over, the blankets will look like they’ve never been touched.
```

```tex
# 中文版本
我很害羞。小学的时候演一个关于游猎的戏剧，别人都扮动物，只有我扮的是草。在演讲大厅里，我从未问过任何问题。在体育课上，我总是躲在角落里。

如果别人撞到了我，我会道歉。街上散发的每张传单我都会接。我总是把购物手推车归到原位。如果咖啡店柜台上的调味奶用完了，我就喝黑咖啡。如果我在别人家过夜，毯子看起来就像没碰过一样平整。
```

```tex
# 合并版本
I AM SHY. In elementary school for a play about a safari, everyone else was an animal. I was grass. I’ve never asked a question in a large lecture hall. 

我很害羞。小学的时候演一个关于游猎的戏剧，别人都扮动物，只有我扮的是草。在演讲大厅里，我从未问过任何问题。在体育课上，我总是躲在角落里。

I’ll apologize if you bump into me. I’ll accept every pamphlet you hand out on the street. I’ve always rolled my shopping cart back to its place of origin. If there’s no more half-and-half on the counter at the coffee shop, I’ll drink my coffee black. If I sleep over, the blankets will look like they’ve never been touched.

如果别人撞到了我，我会道歉。街上散发的每张传单我都会接。我总是把购物手推车归到原位。如果咖啡店柜台上的调味奶用完了，我就喝黑咖啡。如果我在别人家过夜，毯子看起来就像没碰过一样平整。
```

### 实现功能

- [x] 章节自动匹配
- [x] 中英文段落自动对齐
- [x] 准确率可以达到95%以上
- [x] 合并后同时保留两本电子书注释及其跳转链接
- [x] 自动保存进度，重新启动后继续运行
- [x] 理论上支持五十种语言的图书和中文匹配

## 快速上手使用

在安装完相关环境依赖后，将你需要合并的两本epub电子书文件（例如book1.epub, book2.epub) 放在`epubs`文件夹下
```bash
# python3.8 可以替换为任何>=3.8的python版本
# book1.epub为英文版，book2.epub是中文版
python3.8 main.py book1.epub book2.epub
```
整个处理过程会实时更新进度，根据书的大小和晦涩程度，一般耗费5-15分钟就可以完成（如果你有GPU，速度应该会快上很多），请耐心等待。
如果中途中断也没有关系，进度会自动保存，重新运行上述相同命令即可继续执行。
结果会在当前目录下，以`bookname_combined.epub`的形式出现。

### 配置需求
python>=3.8，运行内存>=4GB，翻译功能可能需要科学上网功能
### Windows 系统环境设置
Windows用户需要提前安装Python3与pip3，
如果你的系统python版本>=3.8 直接使用对应的版本即可. 

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```
### Linux 系统环境设置
```bash
sudo apt update
sudo apt-get install python3.8
sudo apt-get install python3-pip
python3.8 -m pip install --upgrade pip
python3.8 -m pip install -r requirements.txt
```
在Google Cloud 上配置过，整个环境的安装流程大概需要五分钟左右

### Docker 运行

```bash
docker image pull troyes233/ebook_aligner
docker container run -it troyes233/ebook_alginer 
```

### 详细参数

```bash
python3.8 main.py --preview true --load true book1.epub book2.epub
```

* `--preview` 是否打开预览功能，会在每个章节对齐后展示对齐内容, 默认开启
* `--load` 是否加载之前的进度，关闭后会重新进行翻译和对齐，默认开启

## 性能测试

测试环境，Windows系统，16GB内存，处理器AMD Ryzen 5 5500U, 无GPU加速，理论上支持GPU加速，但是由于本人的贫穷，没办法测试，应该会快很多

| 书名                                                         | 英文字符数量（字节） | 翻译时间(s) | 章节匹配时间(s) | 段落对齐时间(s) | 总耗时(s) |
| ------------------------------------------------------------ | -------------------- | ----------- | --------------- | --------------- | --------- |
| **Know My Name(知晓我姓名)**                                 | 670K                 | 19          | 99              | 389             | 507       |
| The Unwinding(下沉年代)                                      | 969K                 | 90          | 88              | 454             | 551       |
| Soulstealers: The Chinese Sorcery Scare of 1768(**叫魂：1768年中国妖术大恐慌**) | 647K                 | 31          | 21              | 941             | 993       |
| Alexander Hamilton(汉密尔顿传)                               | 2344K                | 50          | 94              | 785             | 929       |
| The Great Transformation(大转型)                             | 855K                 | 30          | 132             | 253             | 415       |

PS: 

* Know My Name一书两个版本包含在本项目中，方便进行测试。

* 翻译API不太稳定，并不适合大规模翻译。
* 《叫魂》 一书由于中文译本涉及大量文言文，段落对齐难度较高，故而耗时额外多。

## 技术细节

技术实现本身并不复杂，主要来说分为以下几个过程

```
   ┌─────────────┐
   │             │
   │  Read Book  │ 
   │             │ 读取epub文件并解析
   │             │
   └──────┬──────┘
          │
          │
   ┌──────▼──────┐
   │             │
   │ Translate   │ 翻译每一章的前几段内容
   │             │
   │             │
   └──────┬──────┘
          │
   ┌──────▼──────┐
   │             │
   │ Page Match  │ 进行章节对齐
   │             │
   │             │
   └──────┬──────┘
          │
          │
   ┌──────▼──────┐
   │             │
   │ Paragraph   │ 对每一章进行段落对齐
   │ Aligning    │
   │             │
   └──────┬──────┘
          │
   ┌──────▼──────┐
   │ Output      │
   │ combined.epub 输出合并完成的epub文件
   │             │
   └─────────────┘
```

* `Translate` 翻译阶段调用的pygtrans的api接口
* `Page Match` 章节匹配，取出每一章的前几段内容，通过计算文本相似度来判断是否匹配。暴力解法就是O($N^2$), 效率太低，这里采用滑动窗口的形式，缩小候选项范围，失败后再开启第二轮搜索，扩大范围。
* `Paragraph Align` 段落对齐，原理基本同上。差别在于段落基本是按照顺序进行排列，所以效率更高。

详情可参考代码内注释，更加详细。

## 未来更新

- [ ] ~~不太可能出客户端，自带一个pytorch实在太大了~~
- [ ] 考虑自建服务器，通过网页前端实现交互，以邮件形式发送运行结果（在我资金充裕的情况下）
- [ ] 理论上算法支持多语言版本（模型自带的50种语言都可）
- [ ] 更快效率的文本相似度/ 文本向量化 模型，有比较懂的大佬请联系我
- [ ] 支持更多的翻译API
- [x] 未来考虑搞docker镜像
