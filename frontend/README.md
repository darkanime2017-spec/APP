# 📚 Gutenberg Paragraph Classification

---

## ![💡 Info](https://img.shields.io/badge/Info-Competition-blue?style=for-the-badge)
<div style="padding:15px; border-left:6px solid #2196F3; background-color:#f1f8ff; margin-bottom:20px;">
Classify <b>paragraphs</b> from English books into their respective authors. Each student will work with <b>3 different authors</b>, each having multiple books. The goal is to predict the author based <b>only on the paragraph text</b>. Think of it as a literary detective game.

<b>Note:</b> Your assigned authors may differ from other students. Check your specific assignment for author names and their corresponding labels (1, 2, 3).
</div>

---

## ![📁 Files](https://img.shields.io/badge/Files-Dataset-green?style=for-the-badge)

### ![🗂️ Folder](https://img.shields.io/badge/data%2F-Folder-blue?style=for-the-badge)
<div style="padding:15px; border-left:6px solid #2196F3; background-color:#f1f8ff; margin-bottom:20px;">
Contains all the <b>book text files</b> (.txt) you'll need for training and testing from your 3 assigned authors.
</div>

---

## ![🛠️ Setup](https://img.shields.io/badge/Setup-Python-red?style=for-the-badge)
<div style="padding:15px; border-left:6px solid #f44336; background-color:#fff1f1; margin-bottom:20px;">
Install necessary packages:

<pre>
pip install nltk pandas scikit-learn
</pre>

And download NLTK resources:

<pre>
import nltk
nltk.download('punkt')
nltk.download('stopwords')
</pre>
</div>

---

## ![📝 Parsing Guide](https://img.shields.io/badge/Parsing-Text-yellow?style=for-the-badge)
<div style="padding:15px; border-left:6px solid #FFEB3B; background-color:#fffde7; margin-bottom:20px;">

<b>⚠️ CRITICAL: Extract ONLY the Actual Book Content!</b>

The text files contain a lot of extra stuff that will hurt your accuracy:
<ul>
<li>Project Gutenberg header and license information</li>
<li>Book titles and author names</li>
<li>Table of contents</li>
<li>Chapter titles and section headings</li>
<li>Transcriber's notes</li>
<li>End-of-book legal text</li>
</ul>

<b>You MUST remove all of this metadata and keep ONLY the actual story/book content!</b>

<b>Why this matters:</b> If you include titles, chapter names, or metadata, your classifier will learn to recognize those patterns instead of the author's actual writing style. This will give you <b>LOW ACCURACY</b> later!

<b>How to do it properly:</b>

<ol>
<li><b>Manually inspect</b> each file to find where the real content starts and ends</li>
<li>For example: In <b>George Bernard Shaw___A Treatise on Parents and Children.txt</b>, the actual book content starts at <b>line 85</b></li>
<li>You need to figure out the starting line for <b>each of your books</b> by opening them and looking</li>
<li>Write code to skip everything before the actual content begins</li>
<li>Also skip chapter titles, section headings, and "THE END" type markers</li>
<li>Extract only the <b>paragraphs of actual text</b></li>
</ol>

<b>Pro tip:</b> Different books start at different line numbers. Don't assume they're all the same! You'll need to handle each book individually or write smart code to detect where content begins.
</div>

---

## ![📝 Required Deliverables](https://img.shields.io/badge/Deliverables-Project-yellow?style=for-the-badge)

### 1️⃣ **Text Processing Notebook** (`text_processing.ipynb`)
<div style="padding:15px; border-left:6px solid #FFEB3B; background-color:#fffde7; margin-bottom:20px;">
This notebook should contain:

<ul>
<li>Code to parse all .txt files from your 3 assigned authors</li>
<li><b>Extract ONLY the actual book content</b> - NO titles, NO table of contents, NO metadata, NO chapter headings!</li>
<li>Split the content into paragraphs</li>
<li>To verify your extraction is correct, <b>print only the first 20 lines and last 20 lines</b> of the cleaned text from one sample book</li>
<li><b>⚠️ DO NOT print the entire text content!</b> (it's too huge for the notebook)</li>
<li>You can keep statistics outputs like: "Extracted 245 paragraphs from Book1.txt"</li>
<li>Save the cleaned paragraphs in a structured format (CSV, pickle, or JSON) for use in the classifier notebook</li>
</ul>

<b>What to display (and you can keep this in your submission):</b>
<ul>
<li><b>First 20 lines and last 20 lines</b> from one sample cleaned text to verify correctness</li>
<li>Number of paragraphs extracted from each book</li>
<li>File names processed</li>
<li>Any summary statistics</li>
</ul>

<b>What NOT to display:</b>
<ul>
<li>The entire text content of books (way too long!)</li>
<li>Full paragraphs from all books (keep it to the 20+20 line sample only)</li>
</ul>
</div>

### 2️⃣ **Classifier Notebook** (`classifier.ipynb`)
<div style="padding:15px; border-left:6px solid #4CAF50; background-color:#f1fff1; margin-bottom:20px;">
This notebook should contain:

<b>Part A: Metadata Preparation</b>
<ul>
<li>Create a CSV file with columns: <b>author_name, file_path, class</b></li>
<li>Classes should be labeled as <b>1, 2, 3</b> (one for each of your 3 authors)</li>
<li><b>Display the first 10 rows using <code>df.head(10)</code></b> (keep this output in your submission!)</li>
</ul>

Example CSV structure:
<pre>
author_name,file_path,class
George Bernard Shaw,data/George Bernard Shaw___Book1.txt,1
George Bernard Shaw,data/George Bernard Shaw___Book2.txt,1
Hamlin Garland,data/Hamlin Garland___Book1.txt,2
...
</pre>

<b>Part B: Text Processing & Classification</b>
<ul>
<li>Load the cleaned paragraphs from the text processing notebook</li>
<li>Clean the text further (remove extra spaces, special characters, lowercase, etc.)</li>
<li>Tokenization (split text into words/tokens)</li>
<li>Build an embedding matrix (choose any method: Word2Vec, FastText, GloVe, etc.)</li>
<li>Apply a classifier of your choice - Logistic Regression, Random Forest, SVM, Neural Network, or even SpongeBob if it works! </li>
<li><b>Display the accuracy</b> of your model (keep this output!)</li>
<li>Optional: Display Precision, Recall, F1-score for bonus points</li>
</ul>
</div>

### 3️⃣ **Embedding File** (`embedding_matrix.txt`)
<div style="padding:15px; border-left:6px solid #9C27B0; background-color:#f3e5f5; margin-bottom:20px;">
<ul>
<li>Save your final embedding matrix as a text file</li>
<li>This file should contain the numerical representation of your vocabulary</li>
<li>Include a header or comment explaining the embedding method used (e.g., "Word2Vec CBOW, dimension=100")</li>
</ul>
</div>

---

## ![⚙️ Workflow Summary](https://img.shields.io/badge/Workflow-ML-blue?style=for-the-badge)
<div style="padding:15px; border-left:6px solid #2196F3; background-color:#f1f8ff; margin-bottom:20px;">
<ul>
  <li><b>Parse</b> files - find where actual content starts (manually inspect each book!)</li>
  <li><b>Extract ONLY</b> the real book content (no metadata, titles, or chapter headings)</li>
  <li><b>Print first 20 + last 20 lines</b> from one sample to verify (keep this output!)</li>
  <li>Save cleaned paragraphs to a file</li>
  <li>Create <b>metadata CSV</b> with author names, file paths, and class labels (1, 2, 3)</li>
  <li>Display <b>df.head(10)</b> (keep this output!)</li>
  <li><b>Clean & tokenize</b> the text</li>
  <li>Generate <b>embeddings</b> and save the matrix</li>
  <li>Train your <b>classifier</b></li>
  <li>Display <b>accuracy</b> (keep this output!)</li>
</ul>

</div>

---

## ![🎯 Grading Criteria](https://img.shields.io/badge/Grading-Criteria-red?style=for-the-badge)
<div style="padding:15px; border-left:6px solid #f44336; background-color:#fff1f1; margin-bottom:20px;">
<ul>
<li><b>Text Processing Notebook:</b> Proper content extraction (no metadata!), first 20 + last 20 lines displayed, paragraph count shown</li>
<li><b>Classifier Notebook:</b> CSV created correctly, df.head(10) displayed, working classifier, accuracy displayed</li>
<li><b>Embedding File:</b> Valid embedding matrix saved</li>
<li><b>Code Quality:</b> Clean, commented, well-organized</li>
<li><b>Accuracy:</b> Higher accuracy = better parsing and feature extraction!</li>
</ul>

<b>If you get low accuracy, it's probably because you included titles, chapter names, or metadata in your training data!</b>
</div>

---

## ![📌 Important Notes](https://img.shields.io/badge/Notes-Read%20Carefully-orange?style=for-the-badge)
<div style="padding:15px; border-left:6px solid #FF9800; background-color:#fff3e0; margin-bottom:20px;">
<ul>
<li>You have <b>3 authors only</b>, labeled as classes 1, 2, 3</li>
<li>Each author has <b>multiple books</b></li>
<li><b>Extract ONLY actual book content</b> - this is critical for good accuracy!</li>
<li>Manually inspect files to find where content starts (it varies by book)</li>
<li><b>Print only first 20 + last 20 lines</b> from one sample text to verify - NOT the entire content!</li>
<li>Keep summary statistics and counts in your output</li>
<li><b>Keep all outputs in classifier.ipynb</b> (df.head(10) and accuracy)</li>
<li>The better your content extraction, the better your accuracy!</li>
</ul>
</div>
