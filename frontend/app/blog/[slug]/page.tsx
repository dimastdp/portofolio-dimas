import { blogPosts } from "@/data/blog-posts";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Calendar, Clock } from "lucide-react";
import styles from "./page.module.css";
import type { Metadata } from "next";

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const post = blogPosts.find((p) => p.slug === params.slug);
  if (!post) return { title: "Post Not Found" };
  
  return {
    title: `${post.title} — Blog`,
    description: post.excerpt,
  };
}

export function generateStaticParams() {
  return blogPosts.map((post) => ({
    slug: post.slug,
  }));
}

export default function BlogPost({ params }: { params: { slug: string } }) {
  const post = blogPosts.find((p) => p.slug === params.slug);
  
  if (!post) {
    notFound();
  }

  // Sederhananya, render MD sebagai HTML string (mengganti format dasar)
  const renderContent = (content: string) => {
    let html = content
      .replace(/^# (.*$)/gim, "<h1>$1</h1>")
      .replace(/^## (.*$)/gim, "<h2>$1</h2>")
      .replace(/^### (.*$)/gim, "<h3>$1</h3>")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/`(.*?)`/g, "<code>$1</code>")
      .replace(/```python([\s\S]*?)```/g, '<pre><code class="language-python">$1</code></pre>')
      .replace(/^\> (.*$)/gim, "<blockquote>$1</blockquote>")
      .replace(/\n\n/g, "</p><p>");
      
    if (!html.startsWith("<h")) {
      html = `<p>${html}</p>`;
    }
    return html;
  };

  return (
    <article className={`container ${styles.container}`}>
      <Link href="/blog" className={styles.backLink}>
        <ArrowLeft size={16} /> Back to Blog
      </Link>
      
      <header className={styles.header}>
        <h1 className={styles.title}>{post.title}</h1>
        
        <div className={styles.meta}>
          <span className={styles.metaItem}>
            <Calendar size={14} />
            {new Date(post.date).toLocaleDateString("id-ID", {
              month: "long",
              year: "numeric",
            })}
          </span>
          <span className={styles.metaItem}>
            <Clock size={14} />
            {post.readTime} min read
          </span>
        </div>
        
        <div className={styles.tags}>
          {post.tags.map((tag) => (
            <span key={tag} className="tag">{tag}</span>
          ))}
        </div>
      </header>

      <div 
        className={styles.content}
        dangerouslySetInnerHTML={{ __html: renderContent(post.content) }}
      />
    </article>
  );
}
