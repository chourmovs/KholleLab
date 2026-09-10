import Image from "next/image";
import styles from "./offline.module.css";

export default function OfflinePage() {
  return (
    <main className={styles.page}>
      <section className={styles.card} aria-labelledby="offline-title">
        <Image
          className={styles.logo}
          src="/assets/brand/khollelab-logo-light.svg"
          alt="KHOLLELAB"
          width={280}
          height={68}
          priority
        />
        <p className={styles.eyebrow}>Connexion interrompue</p>
        <h1 id="offline-title">Service temporairement indisponible</h1>
        <p className={styles.message}>
          KHOLLELAB ne parvient pas à joindre le serveur. Vérifiez votre connexion,
          puis réessayez dans quelques instants.
        </p>
        <form action="/" method="get">
          <button className={styles.retry} type="submit">Réessayer</button>
        </form>
      </section>
    </main>
  );
}
