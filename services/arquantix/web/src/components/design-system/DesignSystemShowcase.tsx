"use client";

import React, { useState } from "react";
import {
  StatusBar,
  CircleButton,
  PinDots,
  NumericKeypad,
  PageHeader,
  Button,
  HomeIndicator,
  VideoBackground,
  LoginBrandLogo,
  StatusBarOverlay,
  ImageWithFallback,
  LoginScreen,
} from "@/components/design-system";

const LOGIN_VIDEO_SRC =
  "/_videos/v1/265fe85ade22452927480c55110e6d0c9f30fd80";

function BackIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M15 18l-6-6 6-6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 5v14M5 12h14"
        stroke="black"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** Icône type Face ID — même taille visuelle que les chiffres du pavé. */
function FaceIdIcon() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 24 24"
      fill="none"
      stroke="black"
      strokeWidth="1.35"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M7 3H5a2 2 0 0 0-2 2v2M17 3h2a2 2 0 0 1 2 2v2M7 21H5a2 2 0 0 1-2-2v-2M17 21h2a2 2 0 0 0 2-2v-2" />
      <path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01" />
    </svg>
  );
}

function PinCodeScreenDemo() {
  const [pin, setPin] = useState<number[]>([]);
  const [selectedNumber, setSelectedNumber] = useState<number | null>(null);
  const PIN_LENGTH = 6;

  const handleNumberPress = (number: number) => {
    if (pin.length < PIN_LENGTH) {
      setPin([...pin, number]);
      setSelectedNumber(number);
      setTimeout(() => setSelectedNumber(null), 150);
    }
  };

  const handleBackspace = () => {
    setPin(pin.slice(0, -1));
  };

  return (
    <div className="bg-[#F5F5F7] min-h-[640px] w-full max-w-[420px] mx-auto flex flex-col rounded-[2rem] overflow-hidden border border-black/[0.06] shadow-[0_8px_40px_rgba(0,0,0,0.08)]">
      <StatusBar
        time="9:41"
        batteryLevel={85}
        showCellular
        showWifi
      />
      <PageHeader
        title="Choose a code"
        titleAlign="left"
        backgroundColor="#F5F5F7"
        description="Haec dum oriens diu perferret, caeli reserato tepore Constantius ex summo matutinae sollemniter signum praepositus statui iussit profecturus."
        leftAction={<CircleButton variant="default" onClick={() => {}} icon={<PlusIcon />} />}
        rightAction={<CircleButton variant="default" onClick={() => {}} icon={<PlusIcon />} />}
      />
      <div className="flex justify-center mt-8 px-4">
        <PinDots
          total={PIN_LENGTH}
          filled={pin.length}
          activeColor="#6155F5"
          inactiveColor="rgba(60, 60, 67, 0.18)"
          size="md"
        />
      </div>
      <div className="flex-1 min-h-[32px]" />
      <div className="flex justify-center">
        <NumericKeypad
          onNumberPress={handleNumberPress}
          onBackspace={handleBackspace}
          selectedNumber={selectedNumber}
          showBackspace
          bottomLeftSlot={<FaceIdIcon />}
          onBottomLeftPress={() => {}}
        />
      </div>
    </div>
  );
}

function ComponentGallery() {
  return (
    <div className="p-8 space-y-10 max-w-3xl mx-auto">
      <section>
        <h2 className="text-xl font-bold mb-4 text-neutral-900">Status bar</h2>
        <div className="space-y-4 bg-white rounded-xl border p-4">
          <StatusBar time="9:41" batteryLevel={100} />
          <StatusBar time="10:30" batteryLevel={50} />
          <StatusBar time="11:45" batteryLevel={20} showWifi={false} />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold mb-4 text-neutral-900">Boutons circulaires</h2>
        <div className="flex flex-wrap gap-4 bg-white rounded-xl border p-4">
          <CircleButton size="sm" variant="default" />
          <CircleButton size="md" variant="primary" />
          <CircleButton size="lg" variant="secondary" />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold mb-4 text-neutral-900">Points PIN</h2>
        <div className="space-y-6 bg-white rounded-xl border p-4">
          <PinDots total={4} filled={0} size="sm" />
          <PinDots total={6} filled={3} size="md" />
          <PinDots total={8} filled={7} size="lg" />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold mb-4 text-neutral-900">Pavé numérique</h2>
        <div className="bg-white rounded-xl border p-4 flex justify-center">
          <NumericKeypad
            onNumberPress={() => {}}
            onBackspace={() => {}}
            showBackspace
          />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold mb-4 text-neutral-900">En-têtes de page</h2>
        <div className="space-y-4 rounded-xl overflow-hidden border">
          <PageHeader title="En-tête simple" />
          <PageHeader
            title="Avec description"
            description="Texte de contexte supplémentaire pour l’utilisateur."
          />
          <PageHeader
            title="Avec actions (centré)"
            description="Gauche et droite : boutons circulaires."
            leftAction={<CircleButton icon={<BackIcon />} />}
            rightAction={<CircleButton icon={<PlusIcon />} />}
          />
          <PageHeader
            title="Titre aligné à gauche"
            titleAlign="left"
            description="Même pattern que l’écran code PIN : texte et sous-titre à gauche."
            leftAction={<CircleButton icon={<PlusIcon />} />}
            rightAction={<CircleButton icon={<PlusIcon />} />}
          />
        </div>
      </section>
    </div>
  );
}

function FigmaLoginExportsGallery() {
  return (
    <div className="p-8 space-y-10 max-w-3xl mx-auto border-t bg-neutral-50/80">
      <p className="text-sm text-neutral-600 max-w-2xl">
        Extraits du ZIP « Extraire composants pour Design System » (bouton login,
        barre blanche sur média, logo, indicateur home, vidéo, ImageWithFallback,
        écran Login). Référence textuelle :{" "}
        <code className="text-xs bg-neutral-100 px-1.5 py-0.5 rounded">
          src/components/design-system/DESIGN_SYSTEM.md
        </code>
      </p>

      <section>
        <h2 className="text-xl font-bold mb-4 text-neutral-900">
          Barre de statut (export Figma, texte blanc)
        </h2>
        <div className="rounded-xl overflow-hidden border bg-black p-0">
          <StatusBarOverlay />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold mb-4 text-neutral-900">Logo (écran login)</h2>
        <div className="rounded-xl border bg-black p-8">
          <LoginBrandLogo />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold mb-4 text-neutral-900">
          Boutons Login (primary / secondary)
        </h2>
        <div className="space-y-2 bg-white rounded-xl border p-4 max-w-sm">
          <Button variant="primary" fullWidth>
            Login
          </Button>
          <Button variant="secondary" fullWidth>
            S&apos;inscrire
          </Button>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold mb-4 text-neutral-900">Indicateur home</h2>
        <div className="rounded-xl overflow-hidden border bg-black">
          <HomeIndicator />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold mb-4 text-neutral-900">Fond vidéo</h2>
        <div className="rounded-xl overflow-hidden border h-[200px] w-full max-w-md mx-auto">
          <VideoBackground videoSrc={LOGIN_VIDEO_SRC} />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold mb-4 text-neutral-900">ImageWithFallback</h2>
        <div className="bg-white rounded-xl border p-4">
          <ImageWithFallback
            src="https://invalid.example/no-image.png"
            alt="Démo erreur de chargement"
            className="w-32 h-32 object-cover rounded-md"
          />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold mb-4 text-neutral-900">
          Assemblage type App (375×812)
        </h2>
        <div className="relative w-[375px] h-[812px] mx-auto bg-black rounded-[2rem] overflow-hidden border border-black/10 shadow-lg">
          <VideoBackground videoSrc={LOGIN_VIDEO_SRC}>
            <div className="absolute left-[62px] top-[129px]">
              <LoginBrandLogo />
            </div>
            <div className="absolute top-0 left-0 w-full">
              <StatusBarOverlay />
            </div>
            <div className="absolute left-[16px] top-[645px] w-[343px] flex flex-col gap-[8px]">
              <Button variant="primary" fullWidth>
                Login
              </Button>
              <Button variant="secondary" fullWidth>
                S&apos;inscrire
              </Button>
            </div>
            <div className="absolute bottom-0 left-0 w-full">
              <HomeIndicator />
            </div>
          </VideoBackground>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-bold mb-4 text-neutral-900">
          Composant Login (export Figma)
        </h2>
        <div className="relative w-[375px] h-[812px] mx-auto rounded-[2rem] overflow-hidden border border-black/10 shadow-lg">
          <LoginScreen />
        </div>
      </section>
    </div>
  );
}

export function DesignSystemShowcase() {
  return (
    <div className="pb-16">
      <div className="px-6 py-10 border-b bg-white">
        <p className="text-sm text-neutral-600 max-w-2xl">
          Démos depuis les exports Figma/React : barre de statut paramétrable, en-tête,
          points de code, pavé numérique, boutons circulaires ; plus les composants
          d’écran login du ZIP (voir aussi DESIGN_SYSTEM.md dans ce dossier). Import :{" "}
          <code className="text-xs bg-neutral-100 px-1.5 py-0.5 rounded">
            @/components/design-system
          </code>
        </p>
      </div>
      <div className="py-10 px-4">
        <h2 className="text-center text-lg font-semibold text-neutral-800 mb-6">
          Écran complet (démo interactive)
        </h2>
        <PinCodeScreenDemo />
      </div>
      <ComponentGallery />
      <FigmaLoginExportsGallery />
    </div>
  );
}
