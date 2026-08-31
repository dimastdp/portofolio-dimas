import { blogPosts } from "@/data/blog-posts";
import Link from "next/link";
import { ArrowLeft, Calendar, Clock } from "lucide-react";
import styles from "./page.module.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Blog — Technical Articles",
  description: "Kumpulan artikel teknis tentang civil engineering, data analysis, dan programming.",
};

export default function BlogList() {
  return (
    <div className={`container ${styles.container}`}>
      <div className={styles.header}>
        <Link href="/" className={styles.backLink}>
          <ArrowLeft size={16} /> Back to Home
        </Link>
        <h1 className={styles.title}>Blog</h1>
        <p className={styles.subtitle}>
          Kumpulan artikel teknis, tutorial, dan pengalaman.
        </p>
      </div>

      <div className={styles.grid}>
        {blogPosts.map((post) => (
          <div key={post.slug} className={`card ${styles.card}`}>
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
            
            <h2 className={styles.postTitle}>
              <Link href={`/blog/${post.slug}`}>{post.title}</Link>
            </h2>
            
            <p className={styles.excerpt}>{post.excerpt}</p>
            
            <div className={styles.tags}>
              {post.tags.map((tag) => (
                <span key={tag} className="tag">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
