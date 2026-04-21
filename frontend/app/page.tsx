import { SiteFooter } from "@/components/site/footer";
import { SiteNav } from "@/components/site/nav";
import { Hero } from "@/components/sections/hero";
import { Specimen } from "@/components/sections/specimen";
import { Process } from "@/components/sections/process";
import { Provenance } from "@/components/sections/provenance";
import { MarginRule } from "@/components/margin-rule";

export default function HomePage() {
  return (
    <>
      <SiteNav />
      <main className="relative">
        <MarginRule offsetClass="left-8 md:left-16 xl:left-20" />
        <div className="mx-auto w-full max-w-[1400px]">
          <Hero />
          <Specimen />
          <Process />
          <Provenance />
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
