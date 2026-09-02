"use client";

import { useState } from "react";
import { profile } from "@/data/profile";
import styles from "./Contact.module.css";
import { Mail, MapPin, ExternalLink, Send } from "lucide-react";

export default function Contact() {
  const [formState, setFormState] = useState({
    name: "",
    email: "",
    message: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    // Simulasi pengiriman form (karena belum ada backend)
    setTimeout(() => {
      setIsSubmitting(false);
      setIsSuccess(true);
      setFormState({ name: "", email: "", message: "" });
      
      setTimeout(() => setIsSuccess(false), 3000);
    }, 1500);
  };

  return (
    <section id="contact" className={`section ${styles.contactSection}`}>
      <div className="container">
        <div className="section-header">
          <span className="section-tag">Get in Touch</span>
          <h2 className="section-title">
            Let's <span>Connect</span>
          </h2>
          <p className="section-subtitle">
            Punya proyek menarik atau ingin berdiskusi tentang engineering dan teknologi?
            Jangan ragu untuk menghubungi saya.
          </p>
        </div>

        <div className={styles.grid}>
          {/* Contact Info */}
          <div className={styles.info}>
            <div className={`card ${styles.infoCard}`}>
              <div className={styles.iconWrapper}>
                <MapPin size={24} />
              </div>
              <div>
                <h3>Location</h3>
                <p>{profile.location}</p>
              </div>
            </div>

            <div className={`card ${styles.infoCard}`}>
              <div className={styles.iconWrapper}>
                <Mail size={24} />
              </div>
              <div>
                <h3>Email</h3>
                <a href={`mailto:${profile.email}`}>{profile.email}</a>
              </div>
            </div>

            {profile.linkedin && (
              <div className={`card ${styles.infoCard}`}>
                <div className={styles.iconWrapper}>
                  <ExternalLink size={24} />
                </div>
                <div>
                  <h3>LinkedIn</h3>
                  <a href={profile.linkedin} target="_blank" rel="noopener noreferrer">dimastdp</a>
                </div>
              </div>
            )}

            {profile.instagram && (
              <div className={`card ${styles.infoCard}`}>
                <div className={styles.iconWrapper}>
                  <ExternalLink size={24} />
                </div>
                <div>
                  <h3>Instagram</h3>
                  <a href={`https://instagram.com/${profile.instagram}`} target="_blank" rel="noopener noreferrer">@{profile.instagram}</a>
                </div>
              </div>
            )}
          </div>

          {/* Contact Form */}
          <div className={`card ${styles.formCard}`}>
            <form onSubmit={handleSubmit} className={styles.form}>
              <div className={styles.formGroup}>
                <label htmlFor="name">Name</label>
                <input
                  type="text"
                  id="name"
                  value={formState.name}
                  onChange={(e) => setFormState({ ...formState, name: e.target.value })}
                  required
                  placeholder="John Doe"
                />
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="email">Email</label>
                <input
                  type="email"
                  id="email"
                  value={formState.email}
                  onChange={(e) => setFormState({ ...formState, email: e.target.value })}
                  required
                  placeholder="john@example.com"
                />
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="message">Message</label>
                <textarea
                  id="message"
                  value={formState.message}
                  onChange={(e) => setFormState({ ...formState, message: e.target.value })}
                  required
                  rows={5}
                  placeholder="Hello, I'd like to talk about..."
                />
              </div>

              <button 
                type="submit" 
                className={`btn btn-primary ${styles.submitBtn}`}
                disabled={isSubmitting}
              >
                {isSubmitting ? "Sending..." : isSuccess ? "Message Sent!" : (
                  <>Send Message <Send size={18} /></>
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}
