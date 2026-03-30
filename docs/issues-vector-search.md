# 🧠 BM25 vs Vector Search (HR Example)

## 👩‍💼 Example: HR Knowledge Base Search

### 🔍 Query:

**"How can I take time off next week?"**

---

### 🧠 BM25 (Keyword Search)

BM25 looks for **exact words**.

If documents contain:

- "leave policy"
- "apply leave"
- "vacation request"

👉 Problem:

- "time off" ≠ "leave"
- "take" ≠ "apply"

**Result:**

- ❌ May miss relevant documents
- ❌ Might return less useful results

---

### 🤖 Vector Search

Vector search understands **meaning**.

It connects:

- "time off" → "leave"
- "take leave" → "apply leave"

**Result:**

- ✅ Finds correct HR documents
- ✅ Works even with different wording

---

### ⚡ Another Query

#### 🔍 Query:

**"Leave policy 2025 PDF"**

- **BM25** → ✅ Very accurate (exact match)
- **Vector** → 😐 Less precise for exact file lookup

---

## ⚔️ Summary

- BM25 = exact word matching
- Vector = meaning and intent

---

## 🚀 Best Approach: Hybrid Search

1. User asks:
   **"How can I take time off next week?"**

2. System:
   - BM25 → finds keyword matches
   - Vector → finds semantic matches

3. Combine results → best answer

---

## 🧠 Takeaway

- Users don’t use HR keywords
- They use natural language

👉 Hybrid = best experience

---

# 🎯 Precision vs Recall (Simple Explanation)

## 📌 Scenario

Search: **"leave policy"**

System returns 5 results:

- 3 correct ✅
- 2 wrong ❌

But actually, there are **5 correct documents total**, and system found only 3.

---

## 📌 Precision

👉 Out of shown results, how many are correct?

- 3 correct out of 5

**Precision = 3 / 5 = 60%**

💡 Meaning:

> When system shows something, how often is it right?

---

## 📌 Recall

👉 Out of all correct results, how many did we find?

- Found 3 out of 5

**Recall = 3 / 5 = 60%**

💡 Meaning:

> Did we miss anything important?

---

## 🎣 Simple Analogy (Fishing)

- Precision = how many fish vs trash you caught
- Recall = did you catch most of the fish

---

## ⚖️ Trade-off

### High Precision

- Few results
- Mostly correct
- Might miss some

### High Recall

- Many results
- Includes all correct ones
- Also includes irrelevant ones

---

## 👩‍💼 HR Example

Query: **"work from home policy"**

### High Precision System

- Shows 2 results
- Both correct ✅
- Misses other useful docs ❌

### High Recall System

- Shows 10 results
- Includes all correct ones ✅
- Includes irrelevant ones ❌

---

## 🚀 Final Takeaway

- **Precision** → Are results clean?
- **Recall** → Did we miss anything?

---

```

```
