# Text Preprocessing and Chunking Strategies

Before documents are embedded and indexed, they go through two preparation stages: **text cleaning** and **chunking**. The quality of both directly affects retrieval accuracy.

---

## 1. Text Cleaning and Preprocessing

Raw text extracted from PDFs and other sources often contains noise that degrades embedding quality. Common cleaning steps:

```
| Issue              | Example                 | Fix                         |
| ------------------ | ----------------------- | --------------------------- | ---------------------------- |
| Extra whitespace   | `"hello   world"`       | Strip and normalize spaces  |
| Broken line breaks | `"continu-\nued"`       | Rejoin hyphenated words     |
| Headers / footers  | `"Page 12 .Confidential"`| Remove repeating boilerplate |
| Special characters | `"\x0c"`, `"\u200b"`    | Strip non-printable unicode |
| HTML/XML tags      | `"<b>Title</b>"`        | Strip markup                |
| Duplicate content  | Same paragraph repeated | Deduplicate before chunking |
```

### In this project

`PyPDFLoader` (or `UnstructuredPDFLoader`) handles basic extraction. For noisy PDFs, switch to `UnstructuredPDFLoader` as noted in `README.md` — it applies layout-aware parsing that reduces extraction errors before any manual cleaning is needed.

---

## 2. Chunking Strategies

Chunking splits a cleaned document into smaller pieces that fit within an embedding model's token limit and carry a focused unit of meaning.

### Fixed-Size Chunking

Splits text every N characters (or tokens), regardless of content boundaries.

```
"The employee must submit... [1000 chars] ...HR portal by Friday."
"The deadline applies to... [1000 chars] ...all departments."
```

- **Pros:** Simple, predictable, fast
- **Cons:** Can cut mid-sentence or mid-concept, losing context
- **Use when:** Text is uniform and structure doesn't matter (logs, tabular data)

---

### Recursive Character Text Splitting

Tries to split on natural boundaries in order: `\n\n` → `\n` → ` ` → character. Falls back to the next separator only when the chunk is still too large.

```python
RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
```

- **Pros:** Respects paragraphs and sentences where possible; graceful fallback
- **Cons:** Still character-based, not semantically aware
- **Use when:** General-purpose text (PDFs, articles, documentation) — **this is what the project uses**

---

### Semantic Chunking

Groups sentences together as long as they are semantically similar (measured by embedding similarity). Starts a new chunk when the topic shifts.

```
Chunk 1: All sentences about "leave policy"
Chunk 2: All sentences about "performance review"
```

- **Pros:** Each chunk has coherent meaning; improves retrieval precision
- **Cons:** Slower (requires embedding at chunking time); variable chunk sizes
- **Use when:** Documents mix multiple topics (e.g., an HR handbook covering many policies)

---

### Comparison Summary

| Strategy                 | Boundary-aware | Semantic quality | Speed   | Best for                    |
| ------------------------ | -------------- | ---------------- | ------- | --------------------------- |
| Fixed-size               | No             | Low              | Fastest | Uniform/structured text     |
| Recursive (this project) | Partial        | Medium           | Fast    | General documents           |
| Semantic                 | Yes            | High             | Slow    | Mixed-topic, long documents |

---

## 3. Chunk Overlap and Optimal Chunk Size

### Chunk Overlap

Overlap repeats the last N characters of a chunk at the start of the next one, ensuring context around a boundary is not lost.

```
Chunk 1: [-------- 1000 chars --------]
Chunk 2:                     [200 overlap][-------- new content --------]
```

**This project:** `chunk_size=1000`, `chunk_overlap=200`

- Too little overlap → important context split across chunks, missed by retrieval
- Too much overlap → redundant chunks, higher storage and embedding cost

A commonly recommended overlap is **10–20% of chunk size**.

---

### Optimal Chunk Size

There is no universal optimal — it depends on your embedding model's token limit and the nature of your content:

| Chunk Size              | Trade-off                                                           |
| ----------------------- | ------------------------------------------------------------------- |
| Small (256–512 chars)   | Precise retrieval, but may lack enough context to answer questions  |
| Medium (512–1500 chars) | Good balance for most Q&A use cases                                 |
| Large (1500–3000 chars) | More context per chunk, but noisier embeddings and slower retrieval |

### Practical guidance

- **Match your embedding model's context window.** `text-embedding-001` supports up to 2048 tokens — stay well under that.
- **Test with your data.** Retrieve a few chunks and read them — if an answer would require combining two consecutive chunks, reduce chunk size or increase overlap.
- **For structured documents** (FAQs, policy docs): smaller chunks (500–800 chars) with moderate overlap work well.
- **For narrative documents** (reports, manuals): larger chunks (1000–1500 chars) retain more reasoning context.
