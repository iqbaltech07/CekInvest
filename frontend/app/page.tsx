import Navbar from "@/components/Navbar";
import Hero from "@/components/landing/Hero";
import HowItWorks from "@/components/landing/HowItWorks";
import FeatureBento from "@/components/landing/FeatureBento";
import Stats from "@/components/landing/Stats";
import Footer from "@/components/Footer";


export default function HomePage() {
  return (
    <>
      <Navbar />
      <main className="flex flex-col flex-1">
        <Hero />
        <HowItWorks />
        <FeatureBento />
        <Stats />
      </main>
      <Footer />
    </>
  );
}
