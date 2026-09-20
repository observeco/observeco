import re
import index_terms

# Lines to leave alone: LaTeX commands, table rows, comments.
SKIP = ("\\", "%", "&", "|", "}", "$")

def tag(text):
    """Tag the first occurrence of each index term per chapter.

    `text` is LaTeX (post-pandoc), so chunk on sectioning commands. Chunking
    matters: without it every term is tagged once for the whole book and the
    index points at a single page.
    """
    chunks = re.split(r"(\\(?:chapter|section)\*?\{)", text)
    out = []
    for chunk in chunks:
        if chunk.startswith("\\"):
            out.append(chunk)
            continue
        seen = set()
        lines = chunk.split("\n")
        for li, line in enumerate(lines):
            st = line.lstrip()
            if not st or st.startswith(SKIP):
                continue
            for pat, entry in index_terms.entries():
                if entry in seen:
                    continue
                m = re.search(r"(?<![\w-])" + re.escape(pat) + r"(?![\w-])", line)
                if m:
                    line = line[:m.end()] + "\\index{" + entry + "}" + line[m.end():]
                    seen.add(entry)
            lines[li] = line
        out.append("\n".join(lines))
    return "".join(out)
