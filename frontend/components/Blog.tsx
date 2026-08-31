"use client";

import { motion } from "framer-motion";
import { blogPosts } from "@/data/blog-posts";
import Link from "next/link";
import styles from "./Blog.module.css";
import { ArrowRight, Calendar, Clock } from "lucide-react";

export default function Blog() {
  // Hanya tampilkan 2 artikel terbaru di home
  const recentPosts = blogPosts.slice(0, 2);

  return (
    <section id="blog" className={`section ${styles.blogSection}`}>
      <div className="container">
        <div className="section-header">
          <span className="section-tag">Writing</span>
          <h2 className="section-title">
            Technical <span>Articles</span>
          </h2>
          <p className="section-subtitle">
            Berbagi wawasan, tutorial, dan pengalaman seputar civil engineering,
            data analysis, dan programming.
          </p>
        </div>

        <div className={styles.grid}>
          {recentPosts.map((post, i) => (
            <motion.div
              key={post.slug}
              className={`card ${styles.card}`}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
            >
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
              
              <h3 className={styles.title}>
                <Link href={`/blog/${post.slug}`}>{post.title}</Link>
              </h3>
              
              <p className={styles.excerpt}>{post.excerpt}</p>
              
              <div className={styles.tags}>
                {post.tags.slice(0, 3).map((tag) => (
                  <span key={tag} className="tag">
                    {tag}
                  </span>
                ))}
              </div>

              <div className={styles.footer}>
                <Link href={`/blog/${post.slug}`} className={styles.readMore}>
                  Read Article <ArrowRight size={16} />
                </Link>
              </div>
            </motion.div>
          ))}
        </div>

        <div className={styles.viewAll}>
          <Link href="/blog" className="btn btn-outline">
            View All Articles →
          </Link>
        </div>
      </div>
    </section>
  );
}
