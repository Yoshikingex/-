import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ArrowRight,
  Bot,
  Building2,
  Cpu,
  Gem,
  Globe,
  LineChart,
  Sparkles,
  Workflow,
} from "lucide-react";

const services = [
  {
    title: "AIシステム開発",
    description:
      "生成AI・機械学習を活用し、業務に直結するWebシステムや社内ツールを設計・開発します。",
    icon: Bot,
  },
  {
    title: "業務効率化・自動化",
    description:
      "定型業務を可視化し、RPAやワークフロー連携で自動化。人的工数とオペレーションコストを削減します。",
    icon: Workflow,
  },
  {
    title: "システム開発・保守",
    description:
      "要件定義から設計、開発、運用保守までワンストップで提供し、長期的な改善サイクルを支援します。",
    icon: Cpu,
  },
  {
    title: "自動売買ソリューション",
    description:
      "仮想通貨・外貨取引に関する知見を活かし、ルールベース／アルゴリズムベースの自動売買環境を構築します。",
    icon: LineChart,
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-50 border-b bg-background/90 backdrop-blur-sm">
        <div className="container mx-auto flex items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent">
              <Sparkles className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <p className="text-lg font-bold">合同会社free&apos;s</p>
              <p className="text-xs text-muted-foreground">AI × 自動化 × 金融テクノロジー</p>
            </div>
          </div>
          <Button asChild>
            <a href="#contact">お問い合わせ</a>
          </Button>
        </div>
      </header>

      <main>
        <section className="bg-gradient-to-b from-background via-secondary/30 to-background py-20 md:py-28">
          <div className="container mx-auto px-4">
            <div className="mx-auto max-w-4xl text-center">
              <Badge className="mb-5">埼玉県川越市のITソリューション企業</Badge>
              <h1 className="mb-6 text-4xl font-bold tracking-tight md:text-6xl">
                AIで業務を最適化し、
                <br />
                事業成長を加速する。
              </h1>
              <p className="mx-auto mb-10 max-w-3xl text-lg text-muted-foreground md:text-xl">
                合同会社free&apos;sは、AIを活用したシステム開発・業務効率化の自動化を中心に、
                仮想通貨や外貨取引分野の自動売買ソリューションまで提供するIT企業です。
              </p>
              <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
                <Button size="lg" asChild>
                  <a href="#services">
                    サービスを見る
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </a>
                </Button>
                <Button size="lg" variant="outline" asChild>
                  <a href="#company">会社情報</a>
                </Button>
              </div>
            </div>
          </div>
        </section>

        <section id="services" className="py-20">
          <div className="container mx-auto px-4">
            <div className="mb-12 text-center">
              <h2 className="mb-4 text-3xl font-bold md:text-4xl">事業内容</h2>
              <p className="mx-auto max-w-2xl text-muted-foreground">
                AI技術と実務経験を融合し、現場で使えるシステムを提供します。
              </p>
            </div>
            <div className="grid gap-6 md:grid-cols-2">
              {services.map(({ title, description, icon: Icon }) => (
                <Card key={title} className="border-2 transition-colors hover:border-primary">
                  <CardHeader>
                    <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle>{title}</CardTitle>
                    <CardDescription className="text-base">{description}</CardDescription>
                  </CardHeader>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-card py-20">
          <div className="container mx-auto grid gap-8 px-4 lg:grid-cols-2">
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-2xl">
                  <Gem className="h-6 w-6 text-accent" />
                  別事業：美容業
                </CardTitle>
                <CardDescription className="text-base">
                  IT事業に加えて美容業も展開。異なる業界で培った運用知見を活かし、サービス品質の向上に取り組んでいます。
                </CardDescription>
              </CardHeader>
            </Card>

            <Card id="company" className="border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-2xl">
                  <Building2 className="h-6 w-6 text-primary" />
                  会社情報
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm md:text-base">
                <p>
                  <span className="font-semibold">会社名：</span>
                  合同会社free&apos;s
                </p>
                <p>
                  <span className="font-semibold">所在地：</span>
                  埼玉県川越市広栄町17-7
                </p>
                <p>
                  <span className="font-semibold">事業領域：</span>
                  AIシステム開発、業務自動化、自動売買システム開発、美容業
                </p>
              </CardContent>
            </Card>
          </div>
        </section>
      </main>

      <footer id="contact" className="border-t py-12">
        <div className="container mx-auto px-4 text-center">
          <p className="mb-2 flex items-center justify-center gap-2 text-lg font-semibold">
            <Globe className="h-5 w-5 text-primary" />
            合同会社free&apos;s
          </p>
          <p className="mb-1 text-muted-foreground">埼玉県川越市広栄町17-7</p>
          <p className="text-sm text-muted-foreground">
            お問い合わせ窓口（メール・電話）はご希望に合わせて追加可能です。
          </p>
          <p className="mt-6 text-xs text-muted-foreground">© 2026 合同会社free&apos;s All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
