"""CPU-only lexical recall for ordinary chat; no embeddings or external calls.

Callers must apply ownership and visibility BEFORE scoring any candidate.
"""
import math
import re
import unicodedata
from collections import Counter


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
                   if not unicodedata.combining(c))


def phrase_match(phrase, text):
    phrase, text = fold(phrase).strip(), fold(text)
    if not phrase:
        return False
    if any("\u2e80" <= c <= "\u9fff" or "\uac00" <= c <= "\ud7af" or
           "\u1000" <= c <= "\u109f" or "\u1780" <= c <= "\u17ff" for c in phrase):
        return phrase in text
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text) is not None


CONCEPTS = {
    "coffee": ("coffee", "cafe", "ca phe", "咖啡", "コーヒー", "커피"),
    "tea": ("tea", "tra", "茶", "お茶", "차"),
    "promise": ("promise", "promised", "commitment", "loi hua", "hua", "承诺", "約束", "약속"),
    "birthday": ("birthday", "sinh nhat", "生日", "誕生日", "생일"),
    "study": ("study", "studying", "homework", "bai tap", "hoc tap", "学习", "勉強", "공부"),
    "work": ("work", "job", "career", "cong viec", "viec lam", "工作", "仕事", "직장"),
}
STOP = set("i me my you your the a an is are was were to of and in on at it this that do did what how about toi minh ban cua la va o mot cai thi co da nay nhung voi em anh".split())


def terms(text):
    normalized = fold(text)
    words = [word for word in re.findall(r"\w+", normalized) if word not in STOP]
    result = list(words)
    # Character bigrams help unspaced scripts; they are not semantic embeddings.
    for word in words:
        if any("\u2e80" <= c <= "\u9fff" or "\u1000" <= c <= "\u109f" or
               "\u1780" <= c <= "\u17ff" for c in word):
            result.extend("bi:" + word[i:i+2] for i in range(len(word)-1))
    result.extend("concept:" + name for name, aliases in CONCEPTS.items()
                  if any(phrase_match(alias, normalized) for alias in aliases))
    return result


def rank_scores(query, contents):
    """BM25 over an authorized candidate set, with length normalization."""
    documents = [Counter(terms(content)) for content in contents]
    query_terms = set(terms(query))
    if not documents or not query_terms:
        return [0.0] * len(documents)
    average = sum(sum(doc.values()) for doc in documents) / len(documents) or 1
    frequencies = Counter(term for doc in documents for term in doc)
    scores = []
    for doc in documents:
        score = 0.0
        for term in query_terms.intersection(doc):
            idf = math.log(1 + (len(documents)-frequencies[term]+.5)/(frequencies[term]+.5))
            tf = doc[term]
            score += idf * tf * 2.2 / (tf + 1.2*(.25+.75*sum(doc.values())/average))
        scores.append(score)
    maximum = max(scores, default=0) or 1
    return [score / maximum for score in scores]


def same_statement(left, right):
    # Fuzzy word overlap can collapse negation, quantities or different names.
    normalize = lambda text: " ".join(text.casefold().split())
    return normalize(left) == normalize(right)
