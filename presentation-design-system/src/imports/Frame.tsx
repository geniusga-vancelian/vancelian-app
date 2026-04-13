import svgPaths from "./svg-y785mg5egn";
import imgTitre from "figma:asset/861170a11f4a4fe1209a5d7dcb40b266cb55f996.png";
import imgFrame34053 from "figma:asset/ab2c9b443ed6af2f791eac2b68697656acd02468.png";
import imgPartieGauche from "figma:asset/477cc21cccabe27f215ceb3852ddcb1aa8bb49dd.png";
import imgImage22 from "figma:asset/89e73e587efe83ff23a892a108d8ae1fc3431883.png";
import imgImage23 from "figma:asset/08152efa5e927c086a37527d77dded55b15845df.png";
import imgImage24 from "figma:asset/04d5a690f0792c1ace471b94c6fef762bd1845a5.png";
import imgImage91 from "figma:asset/01f2d79c06f6f1968ed132cb716722e6d8cd9e0a.png";
import imgNewSarwaLogoNoBg1 from "figma:asset/a317db4898a6fd9e68ba011a7773181d26e2d2de.png";
import imgImage92 from "figma:asset/4d34ef082cb613f0f86bee358f5e83f30d3191af.png";
import imgImage from "figma:asset/bd81af2c3b139e7e3d18ca13c4e1a6e9b2458022.png";
import imgImage1 from "figma:asset/8a44bccc3f2eac3a10163e47f25249c67eb0ef32.png";
import imgFrame2147238773 from "figma:asset/5f529eb7a115a2504e05f35c5f648d8be648e2d5.png";
import imgFrame2147238663 from "figma:asset/3d10c599c35de01201fa37ba01915c924c4b9a58.png";
import imgVector from "figma:asset/0add1094c741dfab6fed434236ea2e27f25c04d2.png";
import imgVector1 from "figma:asset/0add1094c741dfab6fed434236ea2e27f25c04d2.png";
import imgRectangle1 from "figma:asset/47063fddef927be7762e36e27eae69470d3a68c2.png";
import imgVector2 from "figma:asset/78937d306f46e8ba5f76df796bdc54908fc8e9b8.png";
import { imgRectangle } from "./svg-2q6fb";

function Logo() {
  return (
    <div className="h-[58px] overflow-clip relative shrink-0 w-[432px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 432 58">
        <g clipPath="url(#clip0_1_2094)" id="Calque_1">
          <path d={svgPaths.p2b851980} fill="var(--fill-0, #1E1C1B)" id="Vector" />
          <g id="Group 34098">
            <path d={svgPaths.p1c1ef580} fill="var(--fill-0, #1E1C1B)" id="Vector_2" />
            <path d={svgPaths.p1416a000} fill="var(--fill-0, #1E1C1B)" id="Vector_3" />
            <path d={svgPaths.p314cc100} fill="var(--fill-0, #1E1C1B)" id="Vector_4" />
            <path d={svgPaths.p28d0600} fill="var(--fill-0, #1E1C1B)" id="Vector_5" />
            <path d={svgPaths.p1abff300} fill="var(--fill-0, #1E1C1B)" id="Vector_6" />
            <path d={svgPaths.p23c29040} fill="var(--fill-0, #1E1C1B)" id="Vector_7" />
            <path d={svgPaths.p2cf50580} fill="var(--fill-0, #1E1C1B)" id="Vector_8" />
            <path d={svgPaths.p1fe8f880} fill="var(--fill-0, #1E1C1B)" id="Vector_9" />
            <path d={svgPaths.p1e02980} fill="var(--fill-0, #1E1C1B)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2094">
            <rect fill="white" height="58" width="432" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame114() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 859 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="859" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame118() {
  return (
    <div className="content-stretch flex flex-col gap-[48px] items-start relative shrink-0 w-[912px]">
      <p className="font-['Geist:Light',sans-serif] font-light leading-[1.2] relative shrink-0 text-[#8a8a8a] text-[24px] tracking-[7px] uppercase w-full">Pitch DECK</p>
      <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[96px] w-full whitespace-pre-wrap">
        {`Redefining `}
        <br aria-hidden="true" />
        Wealth Management for next-gen investors.
      </p>
      <Frame114 />
    </div>
  );
}

function Titre() {
  return (
    <div className="flex-[1_0_0] min-h-px min-w-px relative w-full" data-name="Titre">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgTitre} />
      <div className="overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex flex-col items-start justify-between p-[120px] relative size-full">
          <Logo />
          <Frame118 />
        </div>
      </div>
    </div>
  );
}

function Frame115() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col h-[1080px] items-start justify-end min-h-px min-w-px relative">
      <Titre />
    </div>
  );
}

function PitchDeck() {
  return (
    <div className="content-stretch flex h-[1080px] items-start overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 01">
      <Frame115 />
      <p className="absolute bottom-[25px] font-['Geist:Regular',sans-serif] font-normal leading-[1.4] left-[60px] text-[#8a8a8a] text-[13px] translate-y-full whitespace-nowrap">Confidential Document</p>
    </div>
  );
}

function Frame1() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian</p>
    </div>
  );
}

function Frame117() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1107 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="1107" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame298() {
  return (
    <div className="content-stretch flex flex-col gap-[40px] items-start relative shrink-0 w-full">
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.2] relative shrink-0 text-[40px] w-full">AI is the new norm</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[24px] tracking-[-1px] w-full">
        Fintech democratized access to markets and crypto → mission accomplished.
        <br aria-hidden="true" />
        As AI reshapes how people search, decide, interact and live, financial advisory must shift to AI-driven guidance.
        <br aria-hidden="true" />
        Access of financial market is the old world, forcing the interface of finance is being rebuilt.
      </p>
    </div>
  );
}

function Frame297() {
  return (
    <div className="content-stretch flex flex-col gap-[40px] items-start relative shrink-0 w-full">
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.2] relative shrink-0 text-[40px] w-full">Performance is Under Pressure</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[24px] tracking-[-1px] w-full">
        Purchasing power is eroding. Markets are ultra-efficient. Alpha is compressed.
        <br aria-hidden="true" />
        Investors are searching for new options of return, private markets and alternative yield
      </p>
    </div>
  );
}

function Frame173() {
  return (
    <div className="content-stretch flex flex-col gap-[64px] items-start relative shrink-0 text-[#1e1c1b] w-full">
      <Frame298 />
      <Frame297 />
    </div>
  );
}

function Layer() {
  return (
    <div className="h-[30px] relative shrink-0 w-[43px]" data-name="Layer_1">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 43 30">
        <g clipPath="url(#clip0_1_2013)" id="Layer_1">
          <path d={svgPaths.p15cb14f0} fill="var(--fill-0, #4F46E5)" id="Vector" />
          <path d={svgPaths.p21001240} fill="var(--fill-0, #4F46E5)" id="Vector_2" />
        </g>
        <defs>
          <clipPath id="clip0_1_2013">
            <rect fill="white" height="30" width="43" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame168() {
  return (
    <div className="content-stretch flex flex-col gap-[15px] items-start relative shrink-0 w-full">
      <Layer />
      <div className="font-['Merriweather:Italic',sans-serif] italic leading-[0] min-w-full relative shrink-0 text-[#1e1c1b] text-[40px] w-[min-content] whitespace-pre-wrap">
        <p className="leading-[1.2] mb-0">
          {`We are entering a new structural cycle in finance as technology accelerates and user expectations evolve. `}
          <br aria-hidden="true" />
          If financial institutions took 10 years to become digital,
        </p>
        <p className="leading-[1.2]">how will they pivot to AI and RWA in the next 24 months?</p>
      </div>
    </div>
  );
}

function Frame37() {
  return (
    <div className="content-stretch flex items-center justify-end relative shrink-0 w-full">
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[0] relative shrink-0 text-[#1e1c1b] text-[0px] text-right whitespace-nowrap">
        <span className="leading-[1.2] text-[24px]">
          Gael Itier
          <br aria-hidden="true" />
        </span>
        <span className="font-['Geist:Regular',sans-serif] font-normal leading-[1.5] text-[#8a8a8a] text-[18px]">{`Founder & CEO Group, Vancelian Group`}</span>
      </p>
    </div>
  );
}

function Frame167() {
  return (
    <div className="content-stretch flex flex-col gap-[30px] items-start relative shrink-0 w-[1078px]">
      <Frame168 />
      <Frame37 />
    </div>
  );
}

function Frame39() {
  return (
    <div className="content-stretch flex flex-col items-center relative shrink-0 w-full">
      <Frame167 />
    </div>
  );
}

function Frame6() {
  return (
    <div className="h-[765px] relative shrink-0 w-full">
      <div className="content-stretch flex flex-col items-start justify-between pb-[40px] px-[60px] relative size-full">
        <Frame173 />
        <Frame39 />
      </div>
    </div>
  );
}

function Frame116() {
  return (
    <div className="absolute content-stretch flex flex-col h-[1080px] items-start left-0 top-0 w-[1280px]">
      <div className="relative shrink-0 w-full" data-name="Titre">
        <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative w-full">
          <Frame1 />
          <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">Context</p>
          <Frame117 />
        </div>
      </div>
      <Frame6 />
    </div>
  );
}

function PartieGauche() {
  return (
    <div className="bg-white flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <Frame116 />
    </div>
  );
}

function Frame38() {
  return (
    <div className="h-[1080px] relative shrink-0 w-[640px]">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <img alt="" className="absolute h-[125.88%] left-[-76.71%] max-w-none top-[-5.28%] w-[253.44%]" src={imgFrame34053} />
      </div>
    </div>
  );
}

function Frame166() {
  return (
    <div className="content-stretch flex gap-[8px] items-center relative shrink-0 w-[122px]">
      <div className="relative shrink-0 size-[12px]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
          <path d={svgPaths.p1000d700} fill="var(--fill-0, #8A8A8A)" id="Vector" />
        </svg>
      </div>
    </div>
  );
}

function Frame2() {
  return (
    <div className="content-stretch flex items-center relative shrink-0 w-full">
      <Frame166 />
    </div>
  );
}

function Frame169() {
  return (
    <div className="absolute h-0 left-[60px] top-px w-[1860px]">
      <div className="absolute inset-[-1px_0_0_0]">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1860 1">
          <g id="Frame 1171276372">
            <line id="Line 3" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x1="53" x2="1799" y1="0.5" y2="0.5" />
          </g>
        </svg>
      </div>
    </div>
  );
}

function PitchDeck1() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex h-[1080px] items-center overflow-clip relative shrink-0 w-full" data-name="Pitch Deck - 02">
      <PartieGauche />
      <Frame38 />
      <div className="absolute bottom-0 content-stretch flex flex-col gap-[48px] h-[40px] items-start justify-center left-0 overflow-clip pl-[60px] py-[20px] w-[1920px]" data-name="Footer">
        <Frame2 />
        <p className="absolute bottom-[25px] font-['Geist:Regular',sans-serif] font-normal leading-[1.4] right-[197px] text-[#8a8a8a] text-[13px] translate-x-full translate-y-full whitespace-nowrap">Confidential Document</p>
        <Frame169 />
      </div>
    </div>
  );
}

function Frame3() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">VANCELIAN</p>
    </div>
  );
}

function Frame120() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 787 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="787" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame119() {
  return (
    <div className="absolute content-stretch flex flex-col h-[1080px] items-start left-0 top-0 w-[960px]">
      <div className="relative shrink-0 w-full" data-name="Titre">
        <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative w-full">
          <Frame3 />
          <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">{`Vision & Mission`}</p>
          <Frame120 />
        </div>
      </div>
    </div>
  );
}

function Frame170() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full">
      <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[0] relative shrink-0 text-[#1e1c1b] text-[0px] w-full whitespace-pre-wrap">
        <span className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] text-[40px]">
          Redefining Wealth Management for a new generation of investors.
          <br aria-hidden="true" />
          <br aria-hidden="true" />
        </span>
        <span className="leading-[1.2] text-[40px]">Orienté performance et expérience utilisateur</span>
      </p>
    </div>
  );
}

function Frame7() {
  return (
    <div className="absolute content-stretch flex flex-col h-[739px] items-start justify-center left-0 pb-[120px] pl-[120px] pr-[60px] top-[291px] w-[743px]">
      <Frame170 />
    </div>
  );
}

function PartieGauche1() {
  return (
    <div className="bg-white flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <Frame119 />
      <Frame7 />
    </div>
  );
}

function Frame121() {
  return <div className="absolute h-[1080px] left-0 top-0 w-[960px]" />;
}

function Frame8() {
  return <div className="absolute h-[1080px] left-0 top-0 w-[960px]" />;
}

function Frame171() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full">
      <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[0] relative shrink-0 text-[#1e1c1b] text-[0px] w-full whitespace-pre-wrap">
        <span className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] text-[40px]">Building a regulated, technology-native platform that leverage Digital assets and AI.</span>
        <span className="leading-[1.2] text-[40px]">
          <br aria-hidden="true" />
          <br aria-hidden="true" />
          RWA
        </span>
      </p>
    </div>
  );
}

function Frame122() {
  return (
    <div className="absolute content-stretch flex flex-col h-[739px] items-start justify-center left-[215px] pb-[120px] pl-[60px] pr-[120px] top-[291px] w-[745px]">
      <Frame171 />
    </div>
  );
}

function PartieGauche2() {
  return (
    <div className="flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgPartieGauche} />
      <div className="absolute inset-[-50.56%_-57.61%_-16.3%_-30.1%]" data-name="Union">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1802.03 1802.05">
          <path d={svgPaths.p47b0080} fill="url(#paint0_linear_1_1876)" id="Union" />
          <defs>
            <linearGradient gradientUnits="userSpaceOnUse" id="paint0_linear_1_1876" x1="7063.89" x2="901.012" y1="-1716.96" y2="1802.05">
              <stop stopColor="white" />
              <stop offset="1" stopColor="#DDDDDD" />
            </linearGradient>
          </defs>
        </svg>
      </div>
      <Frame121 />
      <Frame8 />
      <Frame122 />
    </div>
  );
}

function PitchDeck2() {
  return (
    <div className="bg-white content-stretch flex h-[1080px] items-center overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 03">
      <PartieGauche1 />
      <PartieGauche2 />
      <div className="-translate-x-1/2 absolute h-[944px] left-1/2 top-[276px] w-[446px]" data-name="image 22">
        <img alt="" className="absolute inset-0 max-w-none object-contain pointer-events-none size-full" src={imgImage22} />
      </div>
    </div>
  );
}

function Logo1() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame4() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo1 />
    </div>
  );
}

function Frame60() {
  return (
    <div className="content-stretch flex gap-[16px] items-center justify-center relative shrink-0 w-full">
      <div className="flex h-[0.333px] items-center justify-center relative shrink-0 w-[34px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
        <div className="flex-none rotate-[-0.56deg]">
          <div className="h-0 relative w-[34.002px]">
            <div className="absolute inset-[-7.36px_-2.94%_-7.36px_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.0016 14.7279">
                <path d={svgPaths.p34bcc570} fill="var(--stroke-0, #1E1C1B)" id="Arrow 1" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">De la tokenisation d’actif du monde réel à une expérience IA générative - Allier performance et gestion automatisée</p>
    </div>
  );
}

function Frame124() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1747 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="1747" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame123() {
  return (
    <div className="absolute content-stretch flex flex-col h-[1080px] items-center left-0 top-0 w-[1920px]">
      <div className="relative shrink-0 w-full" data-name="Titre">
        <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative w-full">
          <Frame4 />
          <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">Infrastructure</p>
          <Frame60 />
          <Frame124 />
        </div>
      </div>
    </div>
  );
}

function Frame292() {
  return (
    <div className="bg-white content-stretch flex flex-[1_0_0] h-[124px] items-center justify-center min-h-px min-w-px relative rounded-[9.022px]">
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[40px] whitespace-nowrap">AI</p>
    </div>
  );
}

function Frame80() {
  return (
    <div className="content-stretch flex gap-[48px] h-[162px] items-center justify-center px-[40px] relative shrink-0 w-[1038px]">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgPartieGauche} />
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[28px] w-[292px] whitespace-pre-wrap">
        {`La nouvelle norme `}
        <br aria-hidden="true" />
        AI incontournable
      </p>
      <Frame292 />
    </div>
  );
}

function Frame289() {
  return (
    <div className="bg-white content-stretch flex h-[124px] items-center justify-center relative rounded-[9.022px] shrink-0 w-full">
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[40px] whitespace-nowrap">Payment - Core banking</p>
    </div>
  );
}

function Frame290() {
  return (
    <div className="bg-white content-stretch flex h-[124px] items-center justify-center relative rounded-[9.022px] shrink-0 w-full">
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[40px] whitespace-nowrap">Investment engine</p>
    </div>
  );
}

function Frame293() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[10px] items-start min-h-px min-w-px relative">
      <Frame289 />
      <Frame290 />
    </div>
  );
}

function Frame81() {
  return (
    <div className="content-stretch flex gap-[48px] h-[299px] items-center justify-center px-[40px] relative shrink-0 w-[1038px]">
      <div aria-hidden="true" className="absolute inset-0 pointer-events-none">
        <img alt="" className="absolute max-w-none object-cover size-full" src={imgPartieGauche} />
        <div className="absolute bg-[rgba(0,0,0,0.05)] inset-0" />
      </div>
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[28px] w-[292px] whitespace-pre-wrap">
        {`Infrastructure Neobanking `}
        <br aria-hidden="true" />
        et Fintechs
      </p>
      <Frame293 />
    </div>
  );
}

function Frame288() {
  return (
    <div className="bg-white content-stretch flex flex-[1_0_0] h-[124px] items-center justify-center min-h-px min-w-px relative rounded-[9.022px]">
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[40px] whitespace-nowrap">RWA</p>
    </div>
  );
}

function Frame82() {
  return (
    <div className="content-stretch flex gap-[48px] h-[162px] items-center justify-center px-[40px] relative shrink-0 w-[1038px]">
      <div aria-hidden="true" className="absolute inset-0 pointer-events-none">
        <img alt="" className="absolute max-w-none object-cover size-full" src={imgPartieGauche} />
        <div className="absolute bg-[rgba(0,0,0,0.1)] inset-0" />
      </div>
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[28px] w-[292px] whitespace-pre-wrap">
        {`Our Unique `}
        <br aria-hidden="true" />
        Selling Proposal
      </p>
      <Frame288 />
    </div>
  );
}

function Frame294() {
  return (
    <div className="absolute content-stretch flex flex-col items-start left-[822px] overflow-clip rounded-[10px] top-[360px] w-[1038px]">
      <Frame80 />
      <Frame81 />
      <Frame82 />
    </div>
  );
}

function Frame172() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full">
      <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[0] relative shrink-0 text-[#1e1c1b] text-[0px] w-full whitespace-pre-wrap">
        <span className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] text-[40px]">
          Plurimum in amicitia amicorum bene suadentium valeat auctoritas, eaque et adhibeatur ad monendum.
          <br aria-hidden="true" />
          <br aria-hidden="true" />
        </span>
        <span className="leading-[1.2] text-[40px]">{`Haec igitur prima lex amicitiae sanciatur, ut ab amicis honesta petamus, amicorum causa honesta faciamus, ne exspectemus quidem, dum rogemur;  studium semper adsit, cunctatio absit`}</span>
      </p>
    </div>
  );
}

function Frame9() {
  return (
    <div className="absolute content-stretch flex flex-col h-[785px] items-start justify-center left-0 pb-[120px] pt-[60px] px-[60px] top-[295px] w-[743px]">
      <Frame172 />
    </div>
  );
}

function PartieGauche3() {
  return (
    <div className="bg-white flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <Frame123 />
      <Frame294 />
      <Frame9 />
    </div>
  );
}

function PitchDeck3() {
  return (
    <div className="bg-white content-stretch flex items-center overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 04">
      <PartieGauche3 />
    </div>
  );
}

function Logo2() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame5() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo2 />
    </div>
  );
}

function Frame61() {
  return (
    <div className="content-stretch flex gap-[16px] items-center justify-center relative shrink-0 w-full">
      <div className="flex h-[0.333px] items-center justify-center relative shrink-0 w-[34px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
        <div className="flex-none rotate-[-0.56deg]">
          <div className="h-0 relative w-[34.002px]">
            <div className="absolute inset-[-7.36px_-2.94%_-7.36px_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.0016 14.7279">
                <path d={svgPaths.p34bcc570} fill="var(--stroke-0, #1E1C1B)" id="Arrow 1" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">De la tokenisation d’actif du monde réel à une expérience IA générative - Allier performance et gestion automatisée</p>
    </div>
  );
}

function Frame126() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1747 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="1747" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Layer1() {
  return (
    <div className="h-[69px] relative shrink-0 w-[96px]" data-name="Layer_1">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 96 69">
        <g clipPath="url(#clip0_1_2335)" id="Layer_1">
          <path d={svgPaths.p20036500} fill="var(--fill-0, black)" id="Vector" />
          <path d={svgPaths.p2ceabc00} fill="var(--fill-0, black)" id="Vector_2" />
          <path d={svgPaths.p36ed3180} fill="var(--fill-0, black)" id="Vector_3" />
          <path d={svgPaths.p1765700} fill="var(--fill-0, black)" id="Vector_4" />
          <path d={svgPaths.p263c7980} fill="var(--fill-0, black)" id="Vector_5" />
          <path d={svgPaths.p202cbc00} fill="var(--fill-0, black)" id="Vector_6" />
          <path d={svgPaths.p3c4a2800} fill="var(--fill-0, black)" id="Vector_7" />
          <path d={svgPaths.p7ba5380} fill="var(--fill-0, black)" id="Vector_8" />
          <path d={svgPaths.p238a3400} fill="var(--fill-0, black)" id="Vector_9" />
          <path d={svgPaths.p2b51ea80} fill="var(--fill-0, black)" id="Vector_10" />
          <path d={svgPaths.p20e872} fill="var(--fill-0, black)" id="Vector_11" />
          <path d={svgPaths.p3927ea80} fill="var(--fill-0, black)" id="Vector_12" />
          <path d={svgPaths.p110a8c00} fill="var(--fill-0, black)" id="Vector_13" />
          <path d={svgPaths.pd87b880} fill="var(--fill-0, black)" id="Vector_14" />
          <path d={svgPaths.p136db900} fill="var(--fill-0, black)" id="Vector_15" />
          <path d={svgPaths.pe247680} fill="var(--fill-0, black)" id="Vector_16" />
          <path d={svgPaths.p10eded00} fill="var(--fill-0, black)" id="Vector_17" />
          <path d={svgPaths.p30240f80} fill="var(--fill-0, black)" id="Vector_18" />
          <path d={svgPaths.p1cd7c700} fill="var(--fill-0, black)" id="Vector_19" />
          <path d={svgPaths.p27ff9500} fill="var(--fill-0, black)" id="Vector_20" />
          <path d={svgPaths.p39713260} fill="var(--fill-0, black)" id="Vector_21" />
          <path d={svgPaths.p34e9d700} fill="var(--fill-0, black)" id="Vector_22" />
          <path d={svgPaths.p105f8640} fill="var(--fill-0, black)" id="Vector_23" />
          <path d={svgPaths.p15c8d980} fill="var(--fill-0, black)" id="Vector_24" />
        </g>
        <defs>
          <clipPath id="clip0_1_2335">
            <rect fill="white" height="69" width="96" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Avatar() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[174px]" data-name="avatar">
      <Layer1 />
    </div>
  );
}

function Frame46() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-center justify-center min-h-px min-w-px relative">
      <Avatar />
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] min-w-full relative shrink-0 text-[#1e1c1b] text-[40px] text-center w-[min-content]">RWA Tokenization</p>
      <p className="font-['Geist:Light',sans-serif] font-light leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[32px] text-center w-[362px]">Regulated infrastructure to fractionalize Tangible assets like Real Estate, Energy, commodities and Private Equity</p>
    </div>
  );
}

function Calque() {
  return (
    <div className="h-[40px] relative shrink-0 w-[146px]" data-name="Calque_1">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 146 40">
        <g clipPath="url(#clip0_1_2276)" id="Calque_1">
          <path d={svgPaths.p15a02c80} fill="var(--fill-0, #1E1C1B)" id="Vector" />
          <path d={svgPaths.p2d984d00} fill="var(--fill-0, #1E1C1B)" id="Vector_2" />
          <path d={svgPaths.p3f018580} fill="var(--fill-0, #1E1C1B)" id="Vector_3" />
          <path d={svgPaths.p1ac2400} fill="var(--fill-0, #1E1C1B)" id="Vector_4" />
          <path d={svgPaths.p16173200} fill="var(--fill-0, #1E1C1B)" id="Vector_5" />
          <path d={svgPaths.p1e6ea00} fill="var(--fill-0, #1E1C1B)" id="Vector_6" />
          <path d={svgPaths.p1ca1fd00} fill="var(--fill-0, #1E1C1B)" id="Vector_7" />
        </g>
        <defs>
          <clipPath id="clip0_1_2276">
            <rect fill="white" height="40" width="146" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Avatar1() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[174px]" data-name="avatar">
      <Calque />
    </div>
  );
}

function Frame51() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-center justify-center min-h-px min-w-px relative">
      <Avatar1 />
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] min-w-full relative shrink-0 text-[#1e1c1b] text-[40px] text-center w-[min-content]">AI-Driven Advisory</p>
      <p className="font-['Geist:Light',sans-serif] font-light leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[32px] text-center w-[362px]">Intelligent client discovery, dynamic risk profiling and automated allocation through continuous conversational guidance.</p>
    </div>
  );
}

function Layer2() {
  return (
    <div className="relative shrink-0 size-[96px]" data-name="Layer_1">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 96 96">
        <g clipPath="url(#clip0_1_2259)" id="Layer_1">
          <path d={svgPaths.p2e934480} fill="var(--fill-0, #1E1C1B)" id="Vector" />
        </g>
        <defs>
          <clipPath id="clip0_1_2259">
            <rect fill="white" height="96" width="96" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Avatar2() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[174px]" data-name="avatar">
      <Layer2 />
    </div>
  );
}

function Frame52() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-center justify-center min-h-px min-w-px relative">
      <Avatar2 />
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] min-w-full relative shrink-0 text-[#1e1c1b] text-[40px] text-center w-[min-content]">Investment Engine</p>
      <p className="font-['Geist:Light',sans-serif] font-light leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[32px] text-center w-[362px]">A proprietary multi-asset routing infrastructure unifying currencies, crypto, tokenized RWAs and traditional markets.</p>
    </div>
  );
}

function Layer3() {
  return (
    <div className="h-[80px] relative shrink-0 w-[88px]" data-name="Layer_1">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 88 80">
        <g clipPath="url(#clip0_1_2379)" id="Layer_1">
          <path d={svgPaths.p978e5f0} fill="var(--fill-0, #1E1C1B)" id="Vector" />
          <path d={svgPaths.p2dedb500} fill="var(--fill-0, #1E1C1B)" id="Vector_2" />
          <path d={svgPaths.pe4cd00} fill="var(--fill-0, #1E1C1B)" id="Vector_3" />
        </g>
        <defs>
          <clipPath id="clip0_1_2379">
            <rect fill="white" height="80" width="88" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Avatar3() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[174px]" data-name="avatar">
      <Layer3 />
    </div>
  );
}

function Frame53() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-center justify-center min-h-px min-w-px relative">
      <Avatar3 />
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] min-w-full relative shrink-0 text-[#1e1c1b] text-[40px] text-center w-[min-content]">Payment</p>
      <p className="font-['Geist:Light',sans-serif] font-light leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[32px] text-center w-[362px]">Integrated liquidity enabling seamless performance conversion. From portfolio returns to real-world spending.</p>
    </div>
  );
}

function Frame252() {
  return (
    <div className="content-stretch flex gap-[24px] items-start px-[60px] relative shrink-0 w-[1920px]">
      <Frame46 />
      <Frame51 />
      <Frame52 />
      <Frame53 />
    </div>
  );
}

function Frame251() {
  return (
    <div className="content-stretch flex flex-col h-[725px] items-center justify-center pb-[60px] relative shrink-0">
      <Frame252 />
    </div>
  );
}

function Frame125() {
  return (
    <div className="absolute content-stretch flex flex-col h-[1080px] items-center left-0 top-0">
      <div className="relative shrink-0 w-full" data-name="Titre">
        <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative w-full">
          <Frame5 />
          <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">{`Why Tokenization & RWA`}</p>
          <Frame61 />
          <Frame126 />
        </div>
      </div>
      <Frame251 />
    </div>
  );
}

function PartieGauche4() {
  return (
    <div className="bg-white flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <Frame125 />
    </div>
  );
}

function PitchDeck4() {
  return (
    <div className="bg-white content-stretch flex items-center overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 05">
      <PartieGauche4 />
    </div>
  );
}

function Logo3() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame10() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo3 />
    </div>
  );
}

function Frame62() {
  return (
    <div className="content-stretch flex gap-[16px] items-center justify-center relative shrink-0 w-full">
      <div className="flex h-[0.333px] items-center justify-center relative shrink-0 w-[34px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
        <div className="flex-none rotate-[-0.56deg]">
          <div className="h-0 relative w-[34.002px]">
            <div className="absolute inset-[-7.36px_-2.94%_-7.36px_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.0016 14.7279">
                <path d={svgPaths.p34bcc570} fill="var(--stroke-0, #1E1C1B)" id="Arrow 1" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">Sous titre ou phrase d’intro</p>
    </div>
  );
}

function Frame128() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1747 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="1747" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Layer4() {
  return (
    <div className="h-[69px] relative shrink-0 w-[96px]" data-name="Layer_1">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 96 69">
        <g clipPath="url(#clip0_1_2335)" id="Layer_1">
          <path d={svgPaths.p20036500} fill="var(--fill-0, black)" id="Vector" />
          <path d={svgPaths.p2ceabc00} fill="var(--fill-0, black)" id="Vector_2" />
          <path d={svgPaths.p36ed3180} fill="var(--fill-0, black)" id="Vector_3" />
          <path d={svgPaths.p1765700} fill="var(--fill-0, black)" id="Vector_4" />
          <path d={svgPaths.p263c7980} fill="var(--fill-0, black)" id="Vector_5" />
          <path d={svgPaths.p202cbc00} fill="var(--fill-0, black)" id="Vector_6" />
          <path d={svgPaths.p3c4a2800} fill="var(--fill-0, black)" id="Vector_7" />
          <path d={svgPaths.p7ba5380} fill="var(--fill-0, black)" id="Vector_8" />
          <path d={svgPaths.p238a3400} fill="var(--fill-0, black)" id="Vector_9" />
          <path d={svgPaths.p2b51ea80} fill="var(--fill-0, black)" id="Vector_10" />
          <path d={svgPaths.p20e872} fill="var(--fill-0, black)" id="Vector_11" />
          <path d={svgPaths.p3927ea80} fill="var(--fill-0, black)" id="Vector_12" />
          <path d={svgPaths.p110a8c00} fill="var(--fill-0, black)" id="Vector_13" />
          <path d={svgPaths.pd87b880} fill="var(--fill-0, black)" id="Vector_14" />
          <path d={svgPaths.p136db900} fill="var(--fill-0, black)" id="Vector_15" />
          <path d={svgPaths.pe247680} fill="var(--fill-0, black)" id="Vector_16" />
          <path d={svgPaths.p10eded00} fill="var(--fill-0, black)" id="Vector_17" />
          <path d={svgPaths.p30240f80} fill="var(--fill-0, black)" id="Vector_18" />
          <path d={svgPaths.p1cd7c700} fill="var(--fill-0, black)" id="Vector_19" />
          <path d={svgPaths.p27ff9500} fill="var(--fill-0, black)" id="Vector_20" />
          <path d={svgPaths.p39713260} fill="var(--fill-0, black)" id="Vector_21" />
          <path d={svgPaths.p34e9d700} fill="var(--fill-0, black)" id="Vector_22" />
          <path d={svgPaths.p105f8640} fill="var(--fill-0, black)" id="Vector_23" />
          <path d={svgPaths.p15c8d980} fill="var(--fill-0, black)" id="Vector_24" />
        </g>
        <defs>
          <clipPath id="clip0_1_2335">
            <rect fill="white" height="69" width="96" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Avatar4() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[174px]" data-name="avatar">
      <Layer4 />
    </div>
  );
}

function Frame79() {
  return (
    <div className="content-stretch flex flex-col gap-[30px] items-center justify-center leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[40px] text-center w-full">
      <p className="font-['Geist:Bold',sans-serif] font-bold relative shrink-0 w-full">La Tokenisation c’est quoi?</p>
      <p className="font-['Geist:ExtraLight',sans-serif] font-extralight relative shrink-0 w-full">La tokenisation consiste à transformer des actifs illiquides (immobilier, art…) en tokens numériques échangeables, facilitant fractionnement, accessibilité et liquidité.</p>
    </div>
  );
}

function Frame47() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-center min-h-px min-w-px relative">
      <Avatar4 />
      <Frame79 />
    </div>
  );
}

function TrendUp() {
  return (
    <div className="relative shrink-0 size-[63px]" data-name=".trend-up-01">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 63 63">
        <g id=".trend-up-01">
          <path d={svgPaths.p19584480} fill="var(--fill-0, #1E1C1B)" id="Solid" />
        </g>
      </svg>
    </div>
  );
}

function Avatar5() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[174px]" data-name="avatar">
      <TrendUp />
    </div>
  );
}

function Frame83() {
  return (
    <div className="content-stretch flex flex-col gap-[30px] items-center justify-center leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[40px] text-center w-full">
      <p className="font-['Geist:Bold',sans-serif] font-bold relative shrink-0 w-full">La quête de performance</p>
      <p className="font-['Geist:ExtraLight',sans-serif] font-extralight relative shrink-0 w-full">Devenus accessibles et efficients, les marchés cotés poussent les investisseurs vers le non coté, la dette privée et l’immobilier pour chercher davantage de rendement.</p>
    </div>
  );
}

function Frame50() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-center min-h-px min-w-px relative">
      <Avatar5 />
      <Frame83 />
    </div>
  );
}

function Frame253() {
  return (
    <div className="content-stretch flex gap-[90px] items-start px-[60px] relative shrink-0 w-[1920px]">
      <Frame47 />
      <Frame50 />
    </div>
  );
}

function Frame268() {
  return (
    <div className="content-stretch flex flex-col h-[552px] items-start justify-center pb-[60px] relative shrink-0">
      <Frame253 />
    </div>
  );
}

function Frame127() {
  return (
    <div className="absolute content-stretch flex flex-col h-[1080px] items-center left-0 top-0">
      <div className="relative shrink-0 w-full" data-name="Titre">
        <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative w-full">
          <Frame10 />
          <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">Tokenization RWA, What is it? and Why?</p>
          <Frame62 />
          <Frame128 />
        </div>
      </div>
      <Frame268 />
    </div>
  );
}

function Frame11() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-full">
      <p className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[52px] whitespace-nowrap">Conclusion: Toknization and RWA is next Bubble.</p>
    </div>
  );
}

function Footer() {
  return (
    <div className="absolute bottom-0 content-stretch flex flex-col gap-[48px] h-[171px] items-center justify-center left-0 overflow-clip p-[60px] w-[1920px]" data-name="Footer">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgPartieGauche} />
      <div className="absolute inset-[-105.85%_62.6%_-105.86%_9.63%]" data-name="Union">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 533.013 533.022">
          <path d={svgPaths.p21871100} fill="url(#paint0_linear_1_2262)" id="Union" />
          <defs>
            <linearGradient gradientUnits="userSpaceOnUse" id="paint0_linear_1_2262" x1="2089.39" x2="266.504" y1="-507.852" y2="533.018">
              <stop stopColor="white" />
              <stop offset="1" stopColor="#DDDDDD" />
            </linearGradient>
          </defs>
        </svg>
      </div>
      <Frame11 />
      <p className="absolute bottom-[48px] font-['Geist:Regular',sans-serif] font-normal leading-[1.4] opacity-50 right-[164px] text-[13px] text-white translate-x-full translate-y-full whitespace-nowrap">Confidential Document</p>
    </div>
  );
}

function PartieGauche5() {
  return (
    <div className="bg-white flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <Frame127 />
      <Footer />
    </div>
  );
}

function PitchDeck7() {
  return (
    <div className="bg-white content-stretch flex items-center overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 25">
      <PartieGauche5 />
    </div>
  );
}

function Logo4() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame12() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo4 />
    </div>
  );
}

function Frame63() {
  return (
    <div className="content-stretch flex gap-[16px] items-center justify-center relative shrink-0 w-full">
      <div className="flex h-[0.333px] items-center justify-center relative shrink-0 w-[34px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
        <div className="flex-none rotate-[-0.56deg]">
          <div className="h-0 relative w-[34.002px]">
            <div className="absolute inset-[-7.36px_-2.94%_-7.36px_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.0016 14.7279">
                <path d={svgPaths.p34bcc570} fill="var(--stroke-0, #1E1C1B)" id="Arrow 1" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">Sous titre ou phrase d’intro</p>
    </div>
  );
}

function Frame130() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1238 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="1238" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame129() {
  return (
    <div className="absolute content-stretch flex flex-col h-[1080px] items-center left-0 top-0 w-[1411px]">
      <div className="relative shrink-0 w-full" data-name="Titre">
        <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative w-full">
          <Frame12 />
          <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">Pourquoi Vancelian ?</p>
          <Frame63 />
          <Frame130 />
        </div>
      </div>
    </div>
  );
}

function Avatar6() {
  return (
    <div className="bg-[#4f46e5] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[88px]" data-name="avatar">
      <div className="relative shrink-0 size-[42px]" data-name="vault">
        <div className="absolute flex inset-[6.25%_9.38%] items-center justify-center">
          <div className="-scale-y-100 flex-none h-[28px] w-[26px]">
            <div className="relative size-full" data-name="Vector">
              <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 34.125 36.75">
                <path d={svgPaths.p2e9f0e70} fill="var(--fill-0, white)" id="Vector" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame84() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-start justify-center leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b]">
      <p className="font-['Geist:Bold',sans-serif] font-bold relative shrink-0 text-[40px] whitespace-nowrap">Verum ad istam omnem orationem brevis est</p>
      <p className="font-['Geist:Light',sans-serif] font-light min-w-full relative shrink-0 text-[32px] w-[min-content]">Confingit intervallata debetur et longa se distributio convivia.</p>
    </div>
  );
}

function Frame48() {
  return (
    <div className="content-stretch flex gap-[30px] items-center justify-center relative shrink-0 w-full">
      <Avatar6 />
      <Frame84 />
    </div>
  );
}

function Avatar7() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[88px]" data-name="avatar">
      <div className="relative shrink-0 size-[42px]" data-name="vault">
        <div className="absolute flex inset-[6.25%_9.38%] items-center justify-center">
          <div className="-scale-y-100 flex-none h-[28px] w-[26px]">
            <div className="relative size-full" data-name="Vector">
              <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 34.125 36.75">
                <path d={svgPaths.p2e9f0e70} fill="var(--fill-0, #1E1C1B)" id="Vector" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame85() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-start justify-center leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b]">
      <p className="font-['Geist:Bold',sans-serif] font-bold relative shrink-0 text-[40px] whitespace-nowrap">Verum ad istam omnem orationem brevis est</p>
      <p className="font-['Geist:Light',sans-serif] font-light min-w-full relative shrink-0 text-[32px] w-[min-content]">Confingit intervallata debetur et longa se distributio convivia.</p>
    </div>
  );
}

function Frame54() {
  return (
    <div className="content-stretch flex gap-[30px] items-center justify-center relative shrink-0 w-full">
      <Avatar7 />
      <Frame85 />
    </div>
  );
}

function Avatar8() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[88px]" data-name="avatar">
      <div className="relative shrink-0 size-[42px]" data-name="vault">
        <div className="absolute flex inset-[6.25%_9.38%] items-center justify-center">
          <div className="-scale-y-100 flex-none h-[28px] w-[26px]">
            <div className="relative size-full" data-name="Vector">
              <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 34.125 36.75">
                <path d={svgPaths.p2e9f0e70} fill="var(--fill-0, #1E1C1B)" id="Vector" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame86() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-start justify-center leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b]">
      <p className="font-['Geist:Bold',sans-serif] font-bold relative shrink-0 text-[40px] whitespace-nowrap">Verum ad istam omnem orationem brevis est</p>
      <p className="font-['Geist:Light',sans-serif] font-light min-w-full relative shrink-0 text-[32px] w-[min-content]">Confingit intervallata debetur et longa se distributio convivia.</p>
    </div>
  );
}

function Frame55() {
  return (
    <div className="content-stretch flex gap-[30px] items-center justify-center relative shrink-0 w-full">
      <Avatar8 />
      <Frame86 />
    </div>
  );
}

function Avatar9() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[88px]" data-name="avatar">
      <div className="relative shrink-0 size-[42px]" data-name="vault">
        <div className="absolute flex inset-[6.25%_9.38%] items-center justify-center">
          <div className="-scale-y-100 flex-none h-[28px] w-[26px]">
            <div className="relative size-full" data-name="Vector">
              <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 34.125 36.75">
                <path d={svgPaths.p2e9f0e70} fill="var(--fill-0, #1E1C1B)" id="Vector" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame87() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-start justify-center leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b]">
      <p className="font-['Geist:Bold',sans-serif] font-bold relative shrink-0 text-[40px] whitespace-nowrap">Verum ad istam omnem orationem brevis est</p>
      <p className="font-['Geist:Light',sans-serif] font-light min-w-full relative shrink-0 text-[32px] w-[min-content]">Confingit intervallata debetur et longa se distributio convivia.</p>
    </div>
  );
}

function Frame49() {
  return (
    <div className="content-stretch flex gap-[30px] items-center justify-center relative shrink-0 w-full">
      <Avatar9 />
      <Frame87 />
    </div>
  );
}

function Frame254() {
  return (
    <div className="content-stretch flex flex-col gap-[70px] items-start justify-center px-[60px] relative shrink-0 w-[1920px]">
      <Frame48 />
      <Frame54 />
      <Frame55 />
      <Frame49 />
    </div>
  );
}

function Frame269() {
  return (
    <div className="absolute content-stretch flex flex-col items-start justify-center left-0 pb-[120px] top-[355px] w-[1410px]">
      <Frame254 />
    </div>
  );
}

function Frame131() {
  return <div className="h-[1080px] shrink-0 w-[960px]" />;
}

function Frame13() {
  return <div className="flex-[1_0_0] min-h-px min-w-px w-[960px]" />;
}

function PartieGauche7() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[48px] h-[1080px] items-center justify-center left-[1411px] overflow-clip p-[60px] top-0 w-[509px]" data-name="Partie Gauche">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgPartieGauche} />
      <Frame131 />
      <Frame13 />
      <div className="absolute inset-[-10.19%_-58.79%_0_-71.91%]" data-name="Union">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1174.22 1189.96">
          <path d={svgPaths.p58bae00} fill="url(#paint0_linear_1_2177)" id="Union" />
          <defs>
            <linearGradient gradientUnits="userSpaceOnUse" id="paint0_linear_1_2177" x1="4602.89" x2="561.016" y1="-1133.77" y2="1143.65">
              <stop stopColor="#B3ADA8" />
              <stop offset="1" stopColor="#F2F2F2" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </div>
  );
}

function PartieGauche6() {
  return (
    <div className="bg-white flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <Frame129 />
      <Frame269 />
      <PartieGauche7 />
      <div className="absolute h-[927px] left-[1120px] top-[345px] w-[433px]" data-name="image 23">
        <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgImage23} />
      </div>
      <div className="absolute h-[927px] left-[1393px] top-[191px] w-[433px]" data-name="image 24">
        <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgImage24} />
      </div>
    </div>
  );
}

function PitchDeck6() {
  return (
    <div className="bg-white content-stretch flex items-center overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 24">
      <PartieGauche6 />
    </div>
  );
}

function Logo5() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame14() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo5 />
    </div>
  );
}

function Frame64() {
  return (
    <div className="content-stretch flex gap-[16px] items-center justify-center relative shrink-0 w-full">
      <div className="flex h-[0.333px] items-center justify-center relative shrink-0 w-[34px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
        <div className="flex-none rotate-[-0.56deg]">
          <div className="h-0 relative w-[34.002px]">
            <div className="absolute inset-[-7.36px_-2.94%_-7.36px_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.0016 14.7279">
                <path d={svgPaths.p34bcc570} fill="var(--stroke-0, #1E1C1B)" id="Arrow 1" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">Sous titre ou phrase d’intro</p>
    </div>
  );
}

function Frame133() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1747 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="1747" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame132() {
  return (
    <div className="absolute content-stretch flex flex-col h-[1080px] items-center left-0 top-0 w-[1920px]">
      <div className="relative shrink-0 w-full" data-name="Titre">
        <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative w-full">
          <Frame14 />
          <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">Pourquoi investir dans Vancelian ?</p>
          <Frame64 />
          <Frame133 />
        </div>
      </div>
    </div>
  );
}

function Group7() {
  return (
    <div className="relative shrink-0 size-[52px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 52 52">
        <g id="Group 35107">
          <circle cx="26" cy="26" fill="var(--fill-0, white)" id="Ellipse 5" r="26" />
          <path d={svgPaths.p874de00} id="Vector" stroke="var(--stroke-0, #4F46E5)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
        </g>
      </svg>
    </div>
  );
}

function Frame77() {
  return (
    <div className="content-stretch flex gap-[20px] items-center relative shrink-0 w-full">
      <Group7 />
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">Venerat auspiciis fulgorem primis atque foedere quo Roma quarum perfectam in quo primis plerumque atque.</p>
    </div>
  );
}

function Group8() {
  return (
    <div className="relative shrink-0 size-[52px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 52 52">
        <g id="Group 35107">
          <circle cx="26" cy="26" fill="var(--fill-0, white)" id="Ellipse 5" r="26" />
          <path d={svgPaths.p874de00} id="Vector" stroke="var(--stroke-0, #4F46E5)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
        </g>
      </svg>
    </div>
  );
}

function Frame88() {
  return (
    <div className="content-stretch flex gap-[20px] items-center relative shrink-0 w-full">
      <Group8 />
      <p className="flex-[1_0_0] font-['Geist:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px] whitespace-pre-wrap">{`Angustus levibus insontium angustus suae corpus ad et ad solet angustus  victoriam solet animus increpuisset victoriam quicquid tener quassari.`}</p>
    </div>
  );
}

function Group9() {
  return (
    <div className="relative shrink-0 size-[52px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 52 52">
        <g id="Group 35107">
          <circle cx="26" cy="26" fill="var(--fill-0, white)" id="Ellipse 5" r="26" />
          <path d={svgPaths.p874de00} id="Vector" stroke="var(--stroke-0, #4F46E5)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
        </g>
      </svg>
    </div>
  );
}

function Frame89() {
  return (
    <div className="content-stretch flex gap-[20px] items-center relative shrink-0 w-full">
      <Group9 />
      <p className="flex-[1_0_0] font-['Geist:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px] whitespace-pre-wrap">{`Angustus levibus insontium angustus suae corpus ad et ad solet angustus  victoriam solet animus increpuisset victoriam quicquid tener quassari.`}</p>
    </div>
  );
}

function Group10() {
  return (
    <div className="relative shrink-0 size-[52px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 52 52">
        <g id="Group 35107">
          <circle cx="26" cy="26" fill="var(--fill-0, white)" id="Ellipse 5" r="26" />
          <path d={svgPaths.p874de00} id="Vector" stroke="var(--stroke-0, #4F46E5)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
        </g>
      </svg>
    </div>
  );
}

function Frame90() {
  return (
    <div className="content-stretch flex gap-[20px] items-center relative shrink-0 w-full">
      <Group10 />
      <p className="flex-[1_0_0] font-['Geist:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px] whitespace-pre-wrap">{`Angustus levibus insontium angustus suae corpus ad et ad solet angustus  victoriam solet animus increpuisset victoriam quicquid tener quassari.`}</p>
    </div>
  );
}

function Frame210() {
  return (
    <div className="bg-[#f2f2f2] flex-[1_0_0] h-full min-h-px min-w-px relative rounded-[10px]">
      <div className="content-stretch flex flex-col items-start justify-between p-[60px] relative size-full">
        <Frame77 />
        <Frame88 />
        <Frame89 />
        <Frame90 />
      </div>
    </div>
  );
}

function Frame187() {
  return (
    <div className="absolute content-stretch flex h-[725px] items-start left-0 pb-[60px] px-[60px] top-[355px] w-[1920px]">
      <Frame210 />
    </div>
  );
}

function PartieGauche8() {
  return (
    <div className="bg-white flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <Frame132 />
      <Frame187 />
    </div>
  );
}

function PitchDeck14() {
  return (
    <div className="bg-white content-stretch flex items-center overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 38">
      <PartieGauche8 />
    </div>
  );
}

function Logo6() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame15() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo6 />
    </div>
  );
}

function Frame65() {
  return (
    <div className="content-stretch flex gap-[16px] items-center justify-center relative shrink-0 w-full">
      <div className="flex h-[0.333px] items-center justify-center relative shrink-0 w-[34px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
        <div className="flex-none rotate-[-0.56deg]">
          <div className="h-0 relative w-[34.002px]">
            <div className="absolute inset-[-7.36px_-2.94%_-7.36px_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.0016 14.7279">
                <path d={svgPaths.p34bcc570} fill="var(--stroke-0, #1E1C1B)" id="Arrow 1" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">Sous titre ou phrase d’intro</p>
    </div>
  );
}

function Frame135() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1747 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="1747" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame134() {
  return (
    <div className="absolute content-stretch flex flex-col h-[1080px] items-center left-0 top-0">
      <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative shrink-0 w-[1920px]" data-name="Titre">
        <Frame15 />
        <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">Pourquoi maintenant</p>
        <Frame65 />
        <Frame135 />
      </div>
    </div>
  );
}

function Avatar10() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[174px]" data-name="avatar">
      <div className="relative shrink-0 size-[66px]" data-name="vault">
        <div className="absolute flex inset-[6.25%_9.38%] items-center justify-center">
          <div className="-scale-y-100 flex-none h-[28px] w-[26px]">
            <div className="relative size-full" data-name="Vector">
              <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53.625 57.75">
                <path d={svgPaths.p1cd5f200} fill="var(--fill-0, #1E1C1B)" id="Vector" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame91() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-center justify-center leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b]">
      <p className="font-['Geist:Bold',sans-serif] font-bold relative shrink-0 text-[40px] w-full">Verum ad istam omnem orationem brevis est</p>
      <p className="font-['Geist:Light',sans-serif] font-light relative shrink-0 text-[32px] w-full">Confingit intervallata debetur et longa se distributio convivia.</p>
    </div>
  );
}

function Frame56() {
  return (
    <div className="content-stretch flex flex-[1_0_0] gap-[30px] items-center justify-center min-h-px min-w-px relative">
      <Avatar10 />
      <Frame91 />
    </div>
  );
}

function Avatar11() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[174px]" data-name="avatar">
      <div className="relative shrink-0 size-[66px]" data-name="vault">
        <div className="absolute flex inset-[6.25%_9.38%] items-center justify-center">
          <div className="-scale-y-100 flex-none h-[28px] w-[26px]">
            <div className="relative size-full" data-name="Vector">
              <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53.625 57.75">
                <path d={svgPaths.p1cd5f200} fill="var(--fill-0, #1E1C1B)" id="Vector" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame92() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-center justify-center leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b]">
      <p className="font-['Geist:Bold',sans-serif] font-bold relative shrink-0 text-[40px] w-full">Verum ad istam omnem orationem brevis</p>
      <p className="font-['Geist:Light',sans-serif] font-light relative shrink-0 text-[32px] w-full">Confingit intervallata debetur et longa se distributio convivia.</p>
    </div>
  );
}

function Frame57() {
  return (
    <div className="content-stretch flex flex-[1_0_0] gap-[30px] items-center justify-center min-h-px min-w-px relative">
      <Avatar11 />
      <Frame92 />
    </div>
  );
}

function Frame255() {
  return (
    <div className="content-stretch flex gap-[90px] items-center px-[60px] relative shrink-0 w-[1920px]">
      <Frame56 />
      <Frame57 />
    </div>
  );
}

function Avatar12() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[174px]" data-name="avatar">
      <div className="relative shrink-0 size-[66px]" data-name="vault">
        <div className="absolute flex inset-[6.25%_9.38%] items-center justify-center">
          <div className="-scale-y-100 flex-none h-[28px] w-[26px]">
            <div className="relative size-full" data-name="Vector">
              <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53.625 57.75">
                <path d={svgPaths.p1cd5f200} fill="var(--fill-0, #1E1C1B)" id="Vector" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame93() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-center justify-center leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b]">
      <p className="font-['Geist:Bold',sans-serif] font-bold relative shrink-0 text-[40px] w-full">Verum ad istam omnem orationem brevis est</p>
      <p className="font-['Geist:Light',sans-serif] font-light relative shrink-0 text-[32px] w-full">Confingit intervallata debetur et longa se distributio convivia.</p>
    </div>
  );
}

function Frame58() {
  return (
    <div className="content-stretch flex flex-[1_0_0] gap-[30px] items-center justify-center min-h-px min-w-px relative">
      <Avatar12 />
      <Frame93 />
    </div>
  );
}

function Avatar13() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[174px]" data-name="avatar">
      <div className="relative shrink-0 size-[66px]" data-name="vault">
        <div className="absolute flex inset-[6.25%_9.38%] items-center justify-center">
          <div className="-scale-y-100 flex-none h-[28px] w-[26px]">
            <div className="relative size-full" data-name="Vector">
              <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53.625 57.75">
                <path d={svgPaths.p1cd5f200} fill="var(--fill-0, #1E1C1B)" id="Vector" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame94() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-center justify-center leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b]">
      <p className="font-['Geist:Bold',sans-serif] font-bold relative shrink-0 text-[40px] w-full">Verum ad istam omnem orationem brevis</p>
      <p className="font-['Geist:Light',sans-serif] font-light relative shrink-0 text-[32px] w-full">Confingit intervallata debetur et longa se distributio convivia.</p>
    </div>
  );
}

function Frame59() {
  return (
    <div className="content-stretch flex flex-[1_0_0] gap-[30px] items-center justify-center min-h-px min-w-px relative">
      <Avatar13 />
      <Frame94 />
    </div>
  );
}

function Frame256() {
  return (
    <div className="content-stretch flex gap-[90px] items-center px-[60px] relative shrink-0 w-[1920px]">
      <Frame58 />
      <Frame59 />
    </div>
  );
}

function Frame270() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[60px] h-[621px] items-start justify-center left-0 pb-[120px] top-[355px]">
      <Frame255 />
      <Frame256 />
    </div>
  );
}

function Frame16() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-full">
      <p className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[52px] whitespace-nowrap">Conclusion: ...</p>
    </div>
  );
}

function Footer1() {
  return (
    <div className="absolute bottom-0 content-stretch flex flex-col gap-[48px] h-[171px] items-center justify-center left-0 overflow-clip p-[60px] w-[1920px]" data-name="Footer">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgPartieGauche} />
      <div className="absolute inset-[-105.85%_62.6%_-105.86%_9.63%]" data-name="Union">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 533.013 533.022">
          <path d={svgPaths.p19a3f280} fill="url(#paint0_linear_1_1999)" id="Union" />
          <defs>
            <linearGradient gradientUnits="userSpaceOnUse" id="paint0_linear_1_1999" x1="2089.39" x2="266.504" y1="-507.852" y2="533.018">
              <stop stopColor="white" />
              <stop offset="1" stopColor="#DDDDDD" />
            </linearGradient>
          </defs>
        </svg>
      </div>
      <Frame16 />
      <p className="absolute bottom-[48px] font-['Geist:Regular',sans-serif] font-normal leading-[1.4] opacity-50 right-[164px] text-[13px] text-white translate-x-full translate-y-full whitespace-nowrap">Confidential Document</p>
    </div>
  );
}

function PartieGauche9() {
  return (
    <div className="bg-white flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <Frame134 />
      <Frame270 />
      <Footer1 />
    </div>
  );
}

function PitchDeck15() {
  return (
    <div className="bg-white content-stretch flex items-center overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 41">
      <PartieGauche9 />
    </div>
  );
}

function Logo7() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame17() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo7 />
    </div>
  );
}

function Frame66() {
  return (
    <div className="content-stretch flex gap-[16px] items-center justify-center relative shrink-0 w-full">
      <div className="flex h-[0.333px] items-center justify-center relative shrink-0 w-[34px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
        <div className="flex-none rotate-[-0.56deg]">
          <div className="h-0 relative w-[34.002px]">
            <div className="absolute inset-[-7.36px_-2.94%_-7.36px_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.0016 14.7279">
                <path d={svgPaths.p34bcc570} fill="var(--stroke-0, #1E1C1B)" id="Arrow 1" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">Sous titre ou phrase d’intro</p>
    </div>
  );
}

function Frame137() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1747 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="1747" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Group11() {
  return (
    <div className="relative shrink-0 size-[52px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 52 52">
        <g id="Group 35107">
          <circle cx="26" cy="26" fill="var(--fill-0, white)" id="Ellipse 5" r="26" />
          <path d={svgPaths.p874de00} id="Vector" stroke="var(--stroke-0, #4F46E5)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
        </g>
      </svg>
    </div>
  );
}

function Frame78() {
  return (
    <div className="content-stretch flex gap-[20px] items-center relative shrink-0 w-full">
      <Group11 />
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">Venerat auspiciis fulgorem primis atque foedere quo Roma quarum perfectam in quo primis plerumque atque.</p>
    </div>
  );
}

function Group12() {
  return (
    <div className="relative shrink-0 size-[52px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 52 52">
        <g id="Group 35107">
          <circle cx="26" cy="26" fill="var(--fill-0, white)" id="Ellipse 5" r="26" />
          <path d={svgPaths.p874de00} id="Vector" stroke="var(--stroke-0, #4F46E5)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
        </g>
      </svg>
    </div>
  );
}

function Frame95() {
  return (
    <div className="content-stretch flex gap-[20px] items-center relative shrink-0 w-full">
      <Group12 />
      <p className="flex-[1_0_0] font-['Geist:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px] whitespace-pre-wrap">{`Angustus levibus insontium angustus suae corpus ad et ad solet angustus  victoriam solet animus increpuisset victoriam quicquid tener quassari.`}</p>
    </div>
  );
}

function Group13() {
  return (
    <div className="relative shrink-0 size-[52px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 52 52">
        <g id="Group 35107">
          <circle cx="26" cy="26" fill="var(--fill-0, white)" id="Ellipse 5" r="26" />
          <path d={svgPaths.p874de00} id="Vector" stroke="var(--stroke-0, #4F46E5)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
        </g>
      </svg>
    </div>
  );
}

function Frame96() {
  return (
    <div className="content-stretch flex gap-[20px] items-center relative shrink-0 w-full">
      <Group13 />
      <p className="flex-[1_0_0] font-['Geist:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px] whitespace-pre-wrap">{`Angustus levibus insontium angustus suae corpus ad et ad solet angustus  victoriam solet animus increpuisset victoriam quicquid tener quassari.`}</p>
    </div>
  );
}

function Group14() {
  return (
    <div className="relative shrink-0 size-[52px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 52 52">
        <g id="Group 35107">
          <circle cx="26" cy="26" fill="var(--fill-0, white)" id="Ellipse 5" r="26" />
          <path d={svgPaths.p874de00} id="Vector" stroke="var(--stroke-0, #4F46E5)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
        </g>
      </svg>
    </div>
  );
}

function Frame97() {
  return (
    <div className="content-stretch flex gap-[20px] items-center relative shrink-0 w-full">
      <Group14 />
      <p className="flex-[1_0_0] font-['Geist:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px] whitespace-pre-wrap">{`Angustus levibus insontium angustus suae corpus ad et ad solet angustus  victoriam solet animus increpuisset victoriam quicquid tener quassari.`}</p>
    </div>
  );
}

function Frame211() {
  return (
    <div className="bg-[#f2f2f2] flex-[1_0_0] h-full min-h-px min-w-px relative rounded-[10px]">
      <div className="content-stretch flex flex-col items-start justify-between p-[60px] relative size-full">
        <Frame78 />
        <Frame95 />
        <Frame96 />
        <Frame97 />
      </div>
    </div>
  );
}

function Frame188() {
  return (
    <div className="content-stretch flex h-[725px] items-start pb-[60px] px-[60px] relative shrink-0 w-[1920px]">
      <Frame211 />
    </div>
  );
}

function Frame136() {
  return (
    <div className="absolute content-stretch flex flex-col h-[1080px] items-center left-0 top-0">
      <div className="relative shrink-0 w-full" data-name="Titre">
        <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative w-full">
          <Frame17 />
          <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">Lorem upsum</p>
          <Frame66 />
          <Frame137 />
        </div>
      </div>
      <Frame188 />
    </div>
  );
}

function PartieGauche10() {
  return (
    <div className="bg-white flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <Frame136 />
    </div>
  );
}

function PitchDeck8() {
  return (
    <div className="bg-white content-stretch flex items-center overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 27">
      <PartieGauche10 />
    </div>
  );
}

function Frame275() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[6px] items-center left-[1085.87px] text-center text-white top-[269px] w-[667.265px]">
      <p className="font-['Geist_Mono:Light',sans-serif] font-light h-[28.751px] leading-[1.2] relative shrink-0 text-[24px] uppercase w-full">10 years</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[normal] relative shrink-0 text-[52px] w-full">$10T</p>
    </div>
  );
}

function Frame274() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[6px] items-center left-[1085.87px] text-center text-white top-[487.18px] w-[667.265px]">
      <p className="font-['Geist_Mono:Light',sans-serif] font-light h-[28.751px] leading-[1.2] relative shrink-0 text-[24px] uppercase w-full">3 Years</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[normal] relative shrink-0 text-[52px] w-full">$1T</p>
    </div>
  );
}

function Frame276() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[6px] items-center left-[1085.87px] text-center text-white top-[742.34px] w-[667.265px]">
      <p className="font-['Geist_Mono:Light',sans-serif] font-light h-[28.751px] leading-[1.2] relative shrink-0 text-[24px] uppercase w-full">today</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[normal] relative shrink-0 text-[52px] w-full">$100B</p>
    </div>
  );
}

function CustomerBase() {
  return (
    <div className="absolute contents left-[694px] top-[152px]" data-name="Customer Base">
      <div className="absolute left-[1008px] size-[823px] top-[152px]">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 823 823">
          <circle cx="411.5" cy="411.5" fill="var(--fill-0, #3C3C3C)" id="Ellipse 6" r="411.5" />
        </svg>
      </div>
      <div className="absolute left-[1145.76px] size-[546.271px] top-[428.73px]">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 546.271 546.271">
          <circle cx="273.135" cy="273.135" fill="var(--fill-0, #575757)" id="Ellipse 8" r="273.135" />
        </svg>
      </div>
      <div className="absolute left-[1276.34px] size-[285.115px] top-[689.89px]">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 285.115 285.115">
          <circle cx="142.557" cy="142.557" fill="var(--fill-0, #6C6C6C)" id="Ellipse 7" r="142.557" />
        </svg>
      </div>
      <Frame275 />
      <Frame274 />
      <Frame276 />
      <div className="absolute flex h-0 items-center justify-center left-[694px] top-[811px] w-[632px]">
        <div className="flex-none rotate-180">
          <div className="h-0 relative w-[632px]">
            <div className="absolute inset-[-4px_0_0_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 632 4">
                <line id="Line 50" stroke="var(--stroke-0, #6C6C6C)" strokeWidth="4" x2="632" y1="2" y2="2" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <div className="absolute flex h-0 items-center justify-center left-[694px] top-[552px] w-[632px]">
        <div className="flex-none rotate-180">
          <div className="h-0 relative w-[632px]">
            <div className="absolute inset-[-4px_0_0_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 632 4">
                <line id="Line 51" stroke="var(--stroke-0, #575757)" strokeWidth="4" x2="632" y1="2" y2="2" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <div className="absolute flex h-0 items-center justify-center left-[694px] top-[360px] w-[632px]">
        <div className="flex-none rotate-180">
          <div className="h-0 relative w-[632px]">
            <div className="absolute inset-[-4px_0_0_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 632 4">
                <line id="Line 52" stroke="var(--stroke-0, #3C3C3C)" strokeWidth="4" x2="632" y1="2" y2="2" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Logo8() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame18() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo8 />
    </div>
  );
}

function Frame67() {
  return (
    <div className="content-stretch flex gap-[16px] items-center justify-center relative shrink-0 w-full">
      <div className="flex h-[0.333px] items-center justify-center relative shrink-0 w-[34px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
        <div className="flex-none rotate-[-0.56deg]">
          <div className="h-0 relative w-[34.002px]">
            <div className="absolute inset-[-7.36px_-2.94%_-7.36px_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.0016 14.7279">
                <path d={svgPaths.p34bcc570} fill="var(--stroke-0, #1E1C1B)" id="Arrow 1" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <p className="flex-[1_0_0] font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[40px]">Tokenization will scale in phases</p>
    </div>
  );
}

function Frame138() {
  return (
    <div className="relative shrink-0 w-full">
      <div className="content-stretch flex items-start pr-[900px] relative w-full">
        <div className="h-0 relative shrink-0 w-[53px]">
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
              <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
        <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 847 1">
              <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="847" y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame174() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full">
      <div className="font-['Geist:ExtraLight',sans-serif] font-extralight h-[568px] leading-[0] relative shrink-0 text-[#1e1c1b] text-[0px] w-full whitespace-pre-wrap">
        <p className="mb-0 text-[40px]">
          <span className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2]">
            blablabal
            <br aria-hidden="true" />
            <br aria-hidden="true" />
          </span>
          <span className="leading-[1.2]">The total underlying private asset market exceeds $300–400 trillion.</span>
        </p>
        <p className="leading-[1.2] text-[40px]">Only a fraction will be tokenized over the next decade.</p>
      </div>
    </div>
  );
}

function Frame19() {
  return (
    <div className="absolute content-stretch flex flex-col items-start justify-center left-[60px] pb-[120px] pr-[60px] top-[360px] w-[592px]">
      <Frame174 />
    </div>
  );
}

function CreatableInvestmentPitchTemplate() {
  return (
    <div className="bg-white h-[1080px] overflow-clip relative shrink-0 w-[1920px]" data-name="Creatable Investment Pitch Template | 32">
      <div className="absolute h-[1277px] left-[2947.5px] top-[1565px] w-[1079px]">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 32 32">
          <g id="Rectangle 4206" />
        </svg>
      </div>
      <CustomerBase />
      <div className="absolute content-stretch flex flex-col gap-[48px] items-start left-0 p-[60px] top-0 w-[1920px]" data-name="Titre">
        <Frame18 />
        <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">Market size</p>
        <Frame67 />
        <Frame138 />
      </div>
      <Frame19 />
      <p className="absolute font-['Geist:ExtraLight',sans-serif] font-extralight leading-[0] left-[691px] text-[#6c6c6c] text-[0px] top-[842px] whitespace-nowrap">
        <span className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] text-[40px]">
          2025
          <br aria-hidden="true" />
        </span>
        <span className="leading-[1.2] text-[40px]">Proof of concept</span>
      </p>
      <p className="absolute font-['Geist:ExtraLight',sans-serif] font-extralight leading-[0] left-[691px] text-[#575757] text-[0px] top-[583px] whitespace-pre">
        <span className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] text-[40px]">
          2028
          <br aria-hidden="true" />
        </span>
        <span className="leading-[1.2] text-[40px]">
          {`Meaningful `}
          <br aria-hidden="true" />
          market size
        </span>
      </p>
      <p className="absolute font-['Geist:ExtraLight',sans-serif] font-extralight leading-[0] left-[691px] text-[#3c3c3c] text-[0px] top-[391px] whitespace-nowrap">
        <span className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] text-[40px]">
          2035
          <br aria-hidden="true" />
        </span>
        <span className="leading-[1.2] text-[40px]">Broad adoption</span>
      </p>
    </div>
  );
}

function Frame277() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[6px] items-center left-[1085.87px] text-center text-white top-[269px] w-[667.265px]">
      <p className="font-['Geist_Mono:Light',sans-serif] font-light h-[28.751px] leading-[1.2] relative shrink-0 text-[24px] uppercase w-full">10 years</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[normal] relative shrink-0 text-[52px] w-full">$10T</p>
    </div>
  );
}

function Frame278() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[6px] items-center left-[1085.87px] text-center text-white top-[487.18px] w-[667.265px]">
      <p className="font-['Geist_Mono:Light',sans-serif] font-light h-[28.751px] leading-[1.2] relative shrink-0 text-[24px] uppercase w-full">3 Years</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[normal] relative shrink-0 text-[52px] w-full">$1T</p>
    </div>
  );
}

function CustomerBase1() {
  return (
    <div className="absolute contents left-[694px] top-[269px]" data-name="Customer Base">
      <Frame277 />
      <Frame278 />
      <div className="absolute flex h-0 items-center justify-center left-[694px] top-[872px] w-[444px]">
        <div className="flex-none rotate-180">
          <div className="h-0 relative w-[444px]">
            <div className="absolute inset-[-4px_0_0_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 444 4">
                <line id="Line 52" stroke="var(--stroke-0, #8D857F)" strokeWidth="4" x2="444" y1="2" y2="2" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Logo9() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame20() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo9 />
    </div>
  );
}

function Frame139() {
  return (
    <div className="relative shrink-0 w-full">
      <div className="content-stretch flex items-start pr-[900px] relative w-full">
        <div className="h-0 relative shrink-0 w-[53px]">
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
              <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
        <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 847 1">
              <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="847" y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame175() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-full">
      <p className="font-['Geist:Medium',sans-serif] font-medium h-[568px] leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[40px] w-full">Pendant que les Fintech se battent sur l’accessibilité des marché traditionnel ou les crypto, les clients se tourneront vers le RWA pour plus de performance.</p>
    </div>
  );
}

function Frame21() {
  return (
    <div className="absolute content-stretch flex flex-col items-start justify-center left-[60px] pb-[120px] pr-[60px] top-[284px] w-[592px]">
      <Frame175 />
    </div>
  );
}

function Frame280() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[20px] h-[120.181px] items-start leading-[0] left-[1138.11px] text-white top-[442.94px] w-[264.629px]">
      <div className="flex flex-col font-['Geist:Bold',sans-serif] font-bold justify-center relative shrink-0 text-[24px] w-full">
        <p className="leading-[1.2]">Financial Market</p>
      </div>
      <div className="flex flex-col font-['Geist:Regular',sans-serif] font-normal justify-center relative shrink-0 text-[18px] w-full">
        <p className="leading-[1.5]">Global equities, fixed income, ETFs, Commodities ....</p>
      </div>
    </div>
  );
}

function Frame282() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[20px] h-[58px] items-start leading-[0] left-[1496px] text-white top-[443px] w-[211px]">
      <div className="flex flex-col font-['Geist:Bold',sans-serif] font-bold justify-center relative shrink-0 text-[24px] w-full">
        <p className="leading-[1.2]">Crypto</p>
      </div>
      <div className="flex flex-col font-['Geist:Regular',sans-serif] font-normal justify-center relative shrink-0 text-[18px] w-full">
        <p className="leading-[1.5]">...</p>
      </div>
    </div>
  );
}

function Frame281() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[20px] h-[120.181px] items-center leading-[0] left-[1291.81px] text-white top-[711.04px] w-[254.229px]">
      <div className="flex flex-col font-['Geist:Bold',sans-serif] font-bold justify-center relative shrink-0 text-[24px] w-full">
        <p className="leading-[1.2]">Tokenized RWA</p>
      </div>
      <div className="flex flex-col font-['Geist:Regular',sans-serif] font-normal justify-center relative shrink-0 text-[18px] w-full">
        <p className="leading-[1.5]">Private equity, Private debt, Real estate, Energy, commodities, Art...</p>
      </div>
    </div>
  );
}

function Group5() {
  return (
    <div className="absolute contents left-[1011px] top-[176px]">
      <div className="absolute left-[1011px] size-[817px] top-[176px]">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 817 817">
          <circle cx="408.5" cy="408.5" id="Ellipse 533" r="398.5" stroke="var(--stroke-0, #8D857F)" strokeWidth="20" />
        </svg>
      </div>
      <div className="absolute left-[1078.02px] size-[682.952px] top-[243.02px]">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 682.952 682.952">
          <circle cx="341.476" cy="341.476" fill="var(--fill-0, #333333)" id="Ellipse 532" opacity="0.2" r="341.476" />
        </svg>
      </div>
      <div className="absolute left-[1097.28px] size-[370.878px] top-[321.86px]">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 370.878 370.878">
          <circle cx="185.439" cy="185.439" fill="var(--fill-0, #333333)" id="Ellipse 31" opacity="0.5" r="185.439" />
        </svg>
      </div>
      <div className="absolute left-[1232.87px] size-[370.878px] top-[555.1px]">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 370.878 370.878">
          <circle cx="185.439" cy="185.439" fill="var(--fill-0, #3F8D69)" id="Ellipse 33" opacity="0.5" r="185.439" />
        </svg>
      </div>
      <div className="absolute left-[1369.25px] size-[370.878px] top-[321.86px]">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 370.878 370.878">
          <circle cx="185.439" cy="185.439" fill="var(--fill-0, #4F46E5)" id="Ellipse 32" opacity="0.5" r="185.439" />
        </svg>
      </div>
      <Frame280 />
      <Frame282 />
      <Frame281 />
    </div>
  );
}

function CreatableInvestmentPitchTemplate2() {
  return (
    <div className="bg-white h-[1080px] overflow-clip relative shrink-0 w-[1920px]" data-name="Creatable Investment Pitch Template | 34">
      <div className="absolute h-[1277px] left-[2947.5px] top-[1565px] w-[1079px]">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 32 32">
          <g id="Rectangle 4206" />
        </svg>
      </div>
      <CustomerBase1 />
      <div className="absolute content-stretch flex flex-col gap-[48px] items-start left-0 p-[60px] top-0 w-[1920px]" data-name="Titre">
        <Frame20 />
        <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#333] text-[60px] w-full">Competitive advantages</p>
        <Frame139 />
      </div>
      <Frame21 />
      <p className="absolute font-['Geist:ExtraLight',sans-serif] font-extralight leading-[0] left-[691px] text-[#8d857f] text-[40px] top-[900px] tracking-[-1px] w-[348px]">
        <span className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2]">AI-driven</span>
        <span className="leading-[1.2]">{` Financial Advisory`}</span>
      </p>
      <Group5 />
    </div>
  );
}

function RevenueSource() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[10px] items-start left-[calc(66.67%-33px)] text-[32px] top-[calc(33.33%-21px)] w-[560px]" data-name="Revenue Source">
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold h-[44px] leading-[normal] relative shrink-0 text-[#191819] w-full">{`Management & Performance fees`}</p>
      <p className="font-['Geist:Light',sans-serif] font-light leading-[1.2] relative shrink-0 text-[#1e1c1b] w-full">Lorem ipsum dolor sit amet consectetur. Senectus aliquet aenean risus quis. Neque viverra amet leo nisl. Morbi habitant cras ornare gravida sed arcu tempor elementum nibh sem.</p>
    </div>
  );
}

function RevenueSource1() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[10px] items-start left-[calc(66.67%-33px)] text-[32px] top-[calc(50%+125px)] w-[560px]" data-name="Revenue Source">
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold h-[44px] leading-[normal] relative shrink-0 text-[#191819] w-full">Transaction fees</p>
      <p className="font-['Geist:Light',sans-serif] font-light leading-[1.2] relative shrink-0 text-[#1e1c1b] w-full">Lorem ipsum dolor sit amet consectetur. Senectus aliquet aenean risus quis. Neque viverra amet leo nisl. Morbi habitant cras ornare gravida sed arcu tempor elementum nibh sem.</p>
    </div>
  );
}

function RevenueSource2() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[10px] items-end left-[64px] text-[32px] text-right top-[calc(33.33%-21px)] w-[560px]" data-name="Revenue Source">
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold h-[44px] leading-[normal] relative shrink-0 text-[#191819] w-full">Tokenization</p>
      <p className="font-['Geist:Light',sans-serif] font-light leading-[1.2] relative shrink-0 text-[#1e1c1b] w-full">Lorem ipsum dolor sit amet consectetur. Senectus aliquet aenean risus quis. Neque viverra amet leo nisl. Morbi habitant cras ornare gravida sed arcu tempor elementum nibh sem.</p>
    </div>
  );
}

function RevenueSource3() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[10px] items-end left-[64px] text-[32px] text-right top-[calc(50%+125px)] w-[560px]" data-name="Revenue Source">
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold h-[44px] leading-[normal] relative shrink-0 text-[#191819] w-full">Sales of RWA</p>
      <p className="font-['Geist:Light',sans-serif] font-light leading-[1.2] relative shrink-0 text-[#1e1c1b] w-full">Lorem ipsum dolor sit amet consectetur. Senectus aliquet aenean risus quis. Neque viverra amet leo nisl. Morbi habitant cras ornare gravida sed arcu tempor elementum nibh sem.</p>
    </div>
  );
}

function DonutGraph() {
  return (
    <div className="absolute content-stretch flex flex-col h-[337px] items-center justify-center left-[calc(33.33%+136px)] top-[calc(33.33%+83px)] w-[336px]" data-name="Donut Graph">
      <p className="font-['Neue_Haas_Grotesk_Display_Pro:45_Light',sans-serif] leading-[normal] not-italic relative shrink-0 text-[#191819] text-[78px] text-center whitespace-nowrap">$15M</p>
      <div className="absolute inset-[-0.62%]">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 340.146 341.146">
          <g id="Donut">
            <g id="Ellipse 4">
              <mask fill="black" height="342.01" id="path-1-outside-1_1_2157" maskUnits="userSpaceOnUse" width="340.974" x="-0.828375" y="-1.97942e-05">
                <rect fill="white" height="342.01" width="340.974" x="-0.828375" y="-1.97942e-05" />
                <path d={svgPaths.p44e2f00} />
              </mask>
              <path d={svgPaths.p44e2f00} fill="var(--fill-0, #191819)" />
              <path d={svgPaths.p44e2f00} mask="url(#path-1-outside-1_1_2157)" stroke="var(--stroke-0, white)" strokeWidth="4" />
            </g>
            <g id="Ellipse 3">
              <mask fill="black" height="342.01" id="path-2-outside-2_1_2157" maskUnits="userSpaceOnUse" width="340.974" x="-0.828375" y="-1.97942e-05">
                <rect fill="white" height="342.01" width="340.974" x="-0.828375" y="-1.97942e-05" />
                <path d={svgPaths.p2c60cf00} />
              </mask>
              <path d={svgPaths.p2c60cf00} fill="var(--fill-0, #191819)" />
              <path d={svgPaths.p2c60cf00} mask="url(#path-2-outside-2_1_2157)" stroke="var(--stroke-0, white)" strokeWidth="4" />
            </g>
            <g id="Ellipse 2">
              <mask fill="black" height="342.01" id="path-3-outside-3_1_2157" maskUnits="userSpaceOnUse" width="173.078" x="-0.828375" y="-4.25125e-08">
                <rect fill="white" height="342.01" width="173.078" x="-0.828375" y="-4.25125e-08" />
                <path d={svgPaths.p1f16d400} />
              </mask>
              <path d={svgPaths.p1f16d400} fill="var(--fill-0, #191819)" />
              <path d={svgPaths.p1f16d400} mask="url(#path-3-outside-3_1_2157)" stroke="var(--stroke-0, white)" strokeWidth="4" />
            </g>
            <g id="Ellipse 6">
              <mask fill="black" height="173.078" id="path-4-outside-4_1_2157" maskUnits="userSpaceOnUse" width="173.078" x="-0.828365" y="-4.25125e-08">
                <rect fill="white" height="173.078" width="173.078" x="-0.828365" y="-4.25125e-08" />
                <path d={svgPaths.p2be05400} />
              </mask>
              <path d={svgPaths.p2be05400} fill="var(--fill-0, #191819)" />
              <path d={svgPaths.p2be05400} mask="url(#path-4-outside-4_1_2157)" stroke="var(--stroke-0, white)" strokeWidth="4" />
            </g>
          </g>
        </svg>
      </div>
    </div>
  );
}

function Logo10() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame22() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo10 />
    </div>
  );
}

function Frame140() {
  return (
    <div className="relative shrink-0 w-full">
      <div className="content-stretch flex items-start pr-[900px] relative w-full">
        <div className="h-0 relative shrink-0 w-[53px]">
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
              <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
        <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 847 1">
              <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="847" y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

function CreatableInvestmentPitchTemplate1() {
  return (
    <div className="bg-[#f2f2f2] h-[1080px] overflow-clip relative shrink-0 w-[1920px]" data-name="Creatable Investment Pitch Template | 32">
      <div className="absolute h-[38px] left-[calc(33.33%+24px)] top-[calc(33.33%+97px)] w-[180px]">
        <div className="absolute inset-[-10.53%_-0.42%_0_-2.22%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 184.75 42">
            <path d={svgPaths.p33da6100} fill="var(--stroke-0, #191819)" id="Vector 50" />
          </svg>
        </div>
      </div>
      <div className="absolute flex h-[38px] items-center justify-center left-[calc(50%+70px)] top-[calc(33.33%+97px)] w-[180px]">
        <div className="-scale-y-100 flex-none rotate-180">
          <div className="h-[38px] relative w-[180px]">
            <div className="absolute inset-[-10.53%_-0.42%_0_-2.22%]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 184.75 42">
                <path d={svgPaths.p33da6100} fill="var(--stroke-0, #191819)" id="Vector 51" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <div className="absolute flex h-[38px] items-center justify-center left-[calc(50%+69px)] top-[calc(66.67%+11px)] w-[180px]">
        <div className="flex-none rotate-180">
          <div className="h-[38px] relative w-[180px]">
            <div className="absolute inset-[-10.53%_-0.42%_0_-2.22%]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 184.75 42">
                <path d={svgPaths.p33da6100} fill="var(--stroke-0, #191819)" id="Vector 52" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <div className="absolute flex h-[38px] items-center justify-center left-[calc(33.33%+23px)] top-[calc(66.67%+11px)] w-[180px]">
        <div className="-scale-y-100 flex-none">
          <div className="h-[38px] relative w-[180px]">
            <div className="absolute inset-[-10.53%_-0.42%_0_-2.22%]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 184.75 42">
                <path d={svgPaths.p33da6100} fill="var(--stroke-0, #191819)" id="Vector 53" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <RevenueSource />
      <RevenueSource1 />
      <RevenueSource2 />
      <RevenueSource3 />
      <DonutGraph />
      <div className="absolute content-stretch flex flex-col gap-[48px] items-start left-0 p-[60px] top-0 w-[1920px]" data-name="Titre">
        <Frame22 />
        <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#333] text-[60px] w-full">{`An Hybrid B2B & B2C revenue models`}</p>
        <Frame140 />
      </div>
    </div>
  );
}

function Logo11() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame23() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo11 />
    </div>
  );
}

function Frame141() {
  return (
    <div className="relative shrink-0 w-full">
      <div className="content-stretch flex items-start pr-[900px] relative w-full">
        <div className="h-0 relative shrink-0 w-[53px]">
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
              <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
        <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 847 1">
              <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="847" y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

function Logo12() {
  return (
    <div className="h-[29px] overflow-clip relative shrink-0 w-[218px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 218 29">
        <g clipPath="url(#clip0_1_1948)" id="Calque_1">
          <path d={svgPaths.p2386b700} fill="var(--fill-0, #1E1C1B)" id="Vector" />
          <g id="Group 34098">
            <path d={svgPaths.p2a512600} fill="var(--fill-0, #1E1C1B)" id="Vector_2" />
            <path d={svgPaths.p136fd100} fill="var(--fill-0, #1E1C1B)" id="Vector_3" />
            <path d={svgPaths.p3ba46180} fill="var(--fill-0, #1E1C1B)" id="Vector_4" />
            <path d={svgPaths.p29a14b80} fill="var(--fill-0, #1E1C1B)" id="Vector_5" />
            <path d={svgPaths.p9de5f00} fill="var(--fill-0, #1E1C1B)" id="Vector_6" />
            <path d={svgPaths.p3cab3480} fill="var(--fill-0, #1E1C1B)" id="Vector_7" />
            <path d={svgPaths.p122aa500} fill="var(--fill-0, #1E1C1B)" id="Vector_8" />
            <path d={svgPaths.p1f41c270} fill="var(--fill-0, #1E1C1B)" id="Vector_9" />
            <path d={svgPaths.pf66a600} fill="var(--fill-0, #1E1C1B)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_1948">
            <rect fill="white" height="29" width="218" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame235() {
  return (
    <div className="content-stretch flex flex-col items-center justify-center relative shrink-0 w-[250px]">
      <Logo12 />
    </div>
  );
}

function Frame234() {
  return (
    <div className="content-stretch flex flex-col h-[41px] items-center justify-center relative shrink-0 w-[250px]">
      <div className="relative shrink-0 size-[100px]" data-name="image 91">
        <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgImage91} />
      </div>
    </div>
  );
}

function Frame233() {
  return (
    <div className="content-stretch flex flex-col items-center justify-center relative shrink-0 w-[250px]">
      <div className="h-[24.599px] relative shrink-0 w-[148px]" data-name="New_sarwa_logo_no_bg 1">
        <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgNewSarwaLogoNoBg1} />
      </div>
    </div>
  );
}

function Frame236() {
  return (
    <div className="content-stretch flex flex-col items-center justify-center relative shrink-0 w-[250px]">
      <div className="h-[29px] relative shrink-0 w-[76px]" data-name="image 92">
        <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgImage92} />
      </div>
    </div>
  );
}

function Frame142() {
  return (
    <div className="bg-white h-[81px] relative rounded-br-[4px] shrink-0 w-full">
      <div aria-hidden="true" className="absolute border-b border-solid border-white inset-0 pointer-events-none rounded-br-[4px]" />
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex gap-[30px] items-center px-[32px] py-[10px] relative size-full">
          <div className="flex flex-[1_0_0] flex-col font-['Geist:Bold',sans-serif] font-bold justify-center leading-[0] min-h-px min-w-px relative text-[#1e1c1b] text-[20px] uppercase">
            <p className="leading-[1.2]">Capability</p>
          </div>
          <Frame235 />
          <Frame234 />
          <Frame233 />
          <Frame236 />
        </div>
      </div>
    </div>
  );
}

function Frame41() {
  return (
    <div className="content-stretch flex flex-[1_0_0] items-center justify-center min-h-px min-w-px relative">
      <div className="flex flex-[1_0_0] flex-col font-['Geist:Bold',sans-serif] font-bold justify-center leading-[0] min-h-px min-w-px relative text-[#1e1c1b] text-[28px]">
        <p className="leading-[1.4]">Tokenization RWA</p>
      </div>
    </div>
  );
}

function Frame222() {
  return (
    <div className="relative shrink-0 size-[35.5px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.4998 35.4998">
        <g id="Frame 2147238810">
          <rect fill="var(--fill-0, #3F8D69)" height="35.4998" rx="5" width="35.4998" />
          <path d={svgPaths.p331ba2c0} fill="var(--fill-0, white)" id="Union" />
        </g>
      </svg>
    </div>
  );
}

function Frame237() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-[250px]">
      <Frame222 />
    </div>
  );
}

function Frame221() {
  return (
    <div className="relative shrink-0 size-[35.5px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.4998 35.4998">
        <g id="Frame 2147238810">
          <rect fill="var(--fill-0, #3F8D69)" height="35.4998" rx="5" width="35.4998" />
          <path d={svgPaths.p331ba2c0} fill="var(--fill-0, white)" id="Union" />
        </g>
      </svg>
    </div>
  );
}

function Frame240() {
  return (
    <div className="content-stretch flex flex-col gap-[10px] items-center justify-center relative shrink-0 w-[250px]">
      <Frame221 />
      <div className="flex flex-col font-['Geist:SemiBold',sans-serif] font-semibold justify-center leading-[0] relative shrink-0 text-[18px] text-black whitespace-nowrap">
        <p className="leading-[1.5]">Real estate only</p>
      </div>
    </div>
  );
}

function Frame223() {
  return (
    <div className="relative shrink-0 size-[35.5px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.4998 35.4998">
        <g id="Frame 2147238809">
          <rect fill="var(--fill-0, #C13535)" height="35.4998" rx="5" width="35.4998" />
          <path d={svgPaths.p16fde900} fill="var(--fill-0, white)" id="Union" />
        </g>
      </svg>
    </div>
  );
}

function Frame241() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-[250px]">
      <Frame223 />
    </div>
  );
}

function Frame224() {
  return (
    <div className="relative shrink-0 size-[35.5px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.4998 35.4998">
        <g id="Frame 2147238809">
          <rect fill="var(--fill-0, #C13535)" height="35.4998" rx="5" width="35.4998" />
          <path d={svgPaths.p16fde900} fill="var(--fill-0, white)" id="Union" />
        </g>
      </svg>
    </div>
  );
}

function Frame243() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-[250px]">
      <Frame224 />
    </div>
  );
}

function Frame143() {
  return (
    <div className="bg-[#f2f2f2] flex-[1_0_0] min-h-px min-w-px relative rounded-br-[4px] w-full">
      <div aria-hidden="true" className="absolute border-b border-solid border-white inset-0 pointer-events-none rounded-br-[4px]" />
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex gap-[30px] items-center px-[32px] py-[10px] relative size-full">
          <Frame41 />
          <Frame237 />
          <Frame240 />
          <Frame241 />
          <Frame243 />
        </div>
      </div>
    </div>
  );
}

function Frame42() {
  return (
    <div className="content-stretch flex flex-[1_0_0] items-center justify-center min-h-px min-w-px relative">
      <div className="flex flex-[1_0_0] flex-col font-['Geist:Bold',sans-serif] font-bold justify-center leading-[0] min-h-px min-w-px relative text-[#1e1c1b] text-[28px]">
        <p className="leading-[1.4]">Advisory / Discretionary Mandate</p>
      </div>
    </div>
  );
}

function Frame225() {
  return (
    <div className="relative shrink-0 size-[35.5px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.4998 35.4998">
        <g id="Frame 2147238810">
          <rect fill="var(--fill-0, #3F8D69)" height="35.4998" rx="5" width="35.4998" />
          <path d={svgPaths.p331ba2c0} fill="var(--fill-0, white)" id="Union" />
        </g>
      </svg>
    </div>
  );
}

function Frame238() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-[250px]">
      <Frame225 />
    </div>
  );
}

function Frame220() {
  return (
    <div className="relative shrink-0 size-[35.5px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.4998 35.4998">
        <g id="Frame 2147238809">
          <rect fill="var(--fill-0, #C13535)" height="35.4998" rx="5" width="35.4998" />
          <path d={svgPaths.p16fde900} fill="var(--fill-0, white)" id="Union" />
        </g>
      </svg>
    </div>
  );
}

function Frame242() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-[250px]">
      <Frame220 />
    </div>
  );
}

function Frame226() {
  return (
    <div className="relative shrink-0 size-[35.5px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.4998 35.4998">
        <g id="Frame 2147238810">
          <rect fill="var(--fill-0, #3F8D69)" height="35.4998" rx="5" width="35.4998" />
          <path d={svgPaths.p331ba2c0} fill="var(--fill-0, white)" id="Union" />
        </g>
      </svg>
    </div>
  );
}

function Frame244() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-[250px]">
      <Frame226 />
    </div>
  );
}

function Frame227() {
  return (
    <div className="relative shrink-0 size-[35.5px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.4998 35.4998">
        <g id="Frame 2147238809">
          <rect fill="var(--fill-0, #C13535)" height="35.4998" rx="5" width="35.4998" />
          <path d={svgPaths.p16fde900} fill="var(--fill-0, white)" id="Union" />
        </g>
      </svg>
    </div>
  );
}

function Frame245() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-[250px]">
      <Frame227 />
    </div>
  );
}

function Frame155() {
  return (
    <div className="bg-[#f2f2f2] flex-[1_0_0] min-h-px min-w-px relative rounded-br-[4px] w-full">
      <div aria-hidden="true" className="absolute border-b border-solid border-white inset-0 pointer-events-none rounded-br-[4px]" />
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex gap-[30px] items-center px-[32px] py-[10px] relative size-full">
          <Frame42 />
          <Frame238 />
          <Frame242 />
          <Frame244 />
          <Frame245 />
        </div>
      </div>
    </div>
  );
}

function Frame43() {
  return (
    <div className="content-stretch flex flex-[1_0_0] items-center justify-center min-h-px min-w-px relative">
      <div className="flex flex-[1_0_0] flex-col font-['Geist:Bold',sans-serif] font-bold justify-center leading-[0] min-h-px min-w-px relative text-[#1e1c1b] text-[28px]">
        <p className="leading-[1.4]">{`Payments & Banking Rails`}</p>
      </div>
    </div>
  );
}

function Frame228() {
  return (
    <div className="relative shrink-0 size-[35.5px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.4998 35.4998">
        <g id="Frame 2147238810">
          <rect fill="var(--fill-0, #3F8D69)" height="35.4998" rx="5" width="35.4998" />
          <path d={svgPaths.p331ba2c0} fill="var(--fill-0, white)" id="Union" />
        </g>
      </svg>
    </div>
  );
}

function Frame239() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-[250px]">
      <Frame228 />
    </div>
  );
}

function Frame229() {
  return (
    <div className="relative shrink-0 size-[35.5px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.4998 35.4998">
        <g id="Frame 2147238809">
          <rect fill="var(--fill-0, #C13535)" height="35.4998" rx="5" width="35.4998" />
          <path d={svgPaths.p16fde900} fill="var(--fill-0, white)" id="Union" />
        </g>
      </svg>
    </div>
  );
}

function Frame246() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-[250px]">
      <Frame229 />
    </div>
  );
}

function Frame230() {
  return (
    <div className="relative shrink-0 size-[35.5px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.4998 35.4998">
        <g id="Frame 2147238809">
          <rect fill="var(--fill-0, #C13535)" height="35.4998" rx="5" width="35.4998" />
          <path d={svgPaths.p16fde900} fill="var(--fill-0, white)" id="Union" />
        </g>
      </svg>
    </div>
  );
}

function Frame247() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-[250px]">
      <Frame230 />
    </div>
  );
}

function Frame231() {
  return (
    <div className="relative shrink-0 size-[35.5px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.4998 35.4998">
        <g id="Frame 2147238810">
          <rect fill="var(--fill-0, #3F8D69)" height="35.4998" rx="5" width="35.4998" />
          <path d={svgPaths.p331ba2c0} fill="var(--fill-0, white)" id="Union" />
        </g>
      </svg>
    </div>
  );
}

function Frame248() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-[250px]">
      <Frame231 />
    </div>
  );
}

function Frame156() {
  return (
    <div className="bg-[#f2f2f2] flex-[1_0_0] min-h-px min-w-px relative rounded-br-[4px] w-full">
      <div aria-hidden="true" className="absolute border-b border-solid border-white inset-0 pointer-events-none rounded-br-[4px]" />
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex gap-[30px] items-center px-[32px] py-[10px] relative size-full">
          <Frame43 />
          <Frame239 />
          <Frame246 />
          <Frame247 />
          <Frame248 />
        </div>
      </div>
    </div>
  );
}

function Frame164() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] h-[531px] items-start relative shrink-0 w-full">
      <Frame142 />
      <Frame143 />
      <Frame155 />
      <Frame156 />
      <div className="absolute h-[554px] left-[661px] rounded-[10px] top-[-11px] w-[284px]">
        <div aria-hidden="true" className="absolute border-2 border-[#1e1c1b] border-solid inset-0 pointer-events-none rounded-[10px]" />
      </div>
    </div>
  );
}

function Frame163() {
  return (
    <div className="absolute content-stretch flex flex-col items-start left-[60px] top-[340px] w-[1800px]">
      <Frame164 />
    </div>
  );
}

function CreatableInvestmentPitchTemplate3() {
  return (
    <div className="bg-white h-[1080px] overflow-clip relative shrink-0 w-[1920px]" data-name="Creatable Investment Pitch Template | 35">
      <div className="absolute content-stretch flex flex-col gap-[48px] items-start left-0 p-[60px] top-0 w-[1920px]" data-name="Titre">
        <Frame23 />
        <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#333] text-[60px] w-full">Competition</p>
        <Frame141 />
      </div>
      <Frame163 />
    </div>
  );
}

function Logo13() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame24() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo13 />
    </div>
  );
}

function Frame144() {
  return (
    <div className="relative shrink-0 w-full">
      <div className="content-stretch flex items-start pr-[900px] relative w-full">
        <div className="h-0 relative shrink-0 w-[53px]">
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
              <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
        <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 847 1">
              <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="847" y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

function ModeIsolation() {
  return (
    <div className="col-1 ml-[3px] mt-[3.5px] relative row-1 size-[23px]" data-name="Mode_Isolation">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 23 23">
        <g clipPath="url(#clip0_1_2195)" id="Mode_Isolation">
          <path d={svgPaths.p2e1c0880} fill="var(--fill-0, #FDCC00)" id="Vector" />
          <path d={svgPaths.pe1f5780} fill="var(--fill-0, #FDCC00)" id="Vector_2" />
          <path d={svgPaths.p8322e00} fill="var(--fill-0, #FDCC00)" id="Vector_3" />
          <path d={svgPaths.p2410af00} fill="var(--fill-0, #FDCC00)" id="Vector_4" />
          <path d={svgPaths.p1e715dc0} fill="var(--fill-0, #FDCC00)" id="Vector_5" />
          <path d={svgPaths.p10c86090} fill="var(--fill-0, #FDCC00)" id="Vector_6" />
          <path d={svgPaths.p28e53200} fill="var(--fill-0, #FDCC00)" id="Vector_7" />
          <path d={svgPaths.p19f0bb00} fill="var(--fill-0, #FDCC00)" id="Vector_8" />
          <path d={svgPaths.p290e9880} fill="var(--fill-0, #FDCC00)" id="Vector_9" />
          <path d={svgPaths.p16f4bd80} fill="var(--fill-0, #FDCC00)" id="Vector_10" />
          <path d={svgPaths.p1a3d5380} fill="var(--fill-0, #FDCC00)" id="Vector_11" />
          <path d={svgPaths.p1e3fcc80} fill="var(--fill-0, #FDCC00)" id="Vector_12" />
        </g>
        <defs>
          <clipPath id="clip0_1_2195">
            <rect fill="white" height="23" width="23" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Group6() {
  return (
    <div className="grid-cols-[max-content] grid-rows-[max-content] inline-grid leading-[0] place-items-start relative shrink-0">
      <div className="col-1 ml-0 mt-0 relative rounded-[9px] row-1 size-[30px]" data-name="image">
        <div aria-hidden="true" className="absolute inset-0 pointer-events-none rounded-[9px]">
          <div className="absolute inset-0 overflow-hidden rounded-[9px]">
            <img alt="" className="absolute h-full left-[-25%] max-w-none top-0 w-[150%]" src={imgImage} />
          </div>
          <div className="absolute bg-[#002395] inset-0 rounded-[9px]" />
        </div>
      </div>
      <ModeIsolation />
    </div>
  );
}

function Frame68() {
  return (
    <div className="content-stretch flex gap-[10px] items-center relative shrink-0">
      <div className="relative rounded-[9px] shrink-0 size-[30px]" data-name="image">
        <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-[9px]">
          <img alt="" className="absolute h-full left-[-25%] max-w-none top-0 w-[150%]" src={imgImage} />
        </div>
      </div>
      <Group6 />
    </div>
  );
}

function Frame279() {
  return (
    <div className="content-stretch flex gap-[10px] items-center justify-end relative shrink-0">
      <Frame68 />
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[32px] text-right text-white whitespace-nowrap">France</p>
    </div>
  );
}

function Logo14() {
  return (
    <div className="h-[23px] relative shrink-0 w-[235.263px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 235.263 23.0003">
        <g id="Logo">
          <path d={svgPaths.p150ae900} fill="var(--fill-0, white)" id="Fill-1" />
          <path d={svgPaths.p3ed46380} fill="var(--fill-0, white)" id="Fill-2" />
          <g id="Group-44">
            <path d={svgPaths.pc3a8200} fill="var(--fill-0, white)" id="Fill-3" />
            <path d={svgPaths.p2f503f00} fill="var(--fill-0, white)" id="Fill-5" />
            <path d={svgPaths.p146249c0} fill="var(--fill-0, white)" id="Fill-7" />
            <path d={svgPaths.p11b77880} fill="var(--fill-0, white)" id="Fill-9" />
            <path d={svgPaths.p3416eb80} fill="var(--fill-0, white)" id="Fill-11" />
            <path d={svgPaths.p1f713220} fill="var(--fill-0, white)" id="Fill-13" />
            <path d={svgPaths.p19163100} fill="var(--fill-0, white)" id="Fill-15" />
            <path d={svgPaths.p3664f500} fill="var(--fill-0, white)" id="Fill-17" />
            <path d={svgPaths.p1d110f80} fill="var(--fill-0, white)" id="Fill-19" />
            <path d={svgPaths.p11817400} fill="var(--fill-0, white)" id="Fill-21" />
            <path d={svgPaths.p2f765a80} fill="var(--fill-0, white)" id="Fill-23" />
            <path d={svgPaths.pe1a2ff0} fill="var(--fill-0, white)" id="Fill-24" />
            <path d={svgPaths.p5c1e600} fill="var(--fill-0, white)" id="Fill-25" />
            <path d={svgPaths.p1918d000} fill="var(--fill-0, white)" id="Fill-26" />
            <path d={svgPaths.p17cad900} fill="var(--fill-0, white)" id="Fill-27" />
            <path d={svgPaths.p46a2100} fill="var(--fill-0, white)" id="Fill-28" />
            <path d={svgPaths.pc087f80} fill="var(--fill-0, white)" id="Fill-29" />
            <path d={svgPaths.p12f32980} fill="var(--fill-0, white)" id="Fill-30" />
            <path d={svgPaths.pb14b300} fill="var(--fill-0, white)" id="Fill-31" />
            <path d={svgPaths.p29af8d00} fill="var(--fill-0, white)" id="Fill-32" />
            <path d={svgPaths.p1467bfc0} fill="var(--fill-0, white)" id="Fill-33" />
            <path d={svgPaths.pf2dee80} fill="var(--fill-0, white)" id="Fill-34" />
            <path d={svgPaths.p13ffd1f0} fill="var(--fill-0, white)" id="Fill-35" />
            <path d={svgPaths.p2a36b00} fill="var(--fill-0, white)" id="Fill-36" />
            <path d={svgPaths.p23322d00} fill="var(--fill-0, white)" id="Fill-37" />
            <path d={svgPaths.p3236b400} fill="var(--fill-0, white)" id="Fill-38" />
            <path d={svgPaths.p33b25b80} fill="var(--fill-0, white)" id="Fill-39" />
            <path d={svgPaths.p8021c80} fill="var(--fill-0, white)" id="Fill-40" />
            <path d={svgPaths.p3718c5c0} fill="var(--fill-0, white)" id="Fill-41" />
            <path d={svgPaths.p3ca686f0} fill="var(--fill-0, white)" id="Fill-42" />
            <path d={svgPaths.p372a6b00} fill="var(--fill-0, white)" id="Fill-43" />
          </g>
        </g>
      </svg>
    </div>
  );
}

function Frame283() {
  return (
    <div className="content-stretch flex flex-col gap-[13px] items-end relative w-[454px]">
      <Frame279 />
      <div className="h-0 relative shrink-0 w-full">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 454 1">
            <line id="Line 53" stroke="var(--stroke-0, white)" x2="454" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <Logo14 />
    </div>
  );
}

function Frame69() {
  return (
    <div className="content-stretch flex flex-col items-center justify-center relative shrink-0 size-[30px]">
      <div className="relative rounded-[9px] shrink-0 size-[32px]" data-name="image">
        <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-[9px]">
          <img alt="" className="absolute h-full left-[-12.29%] max-w-none top-0 w-[200%]" src={imgImage1} />
        </div>
      </div>
    </div>
  );
}

function Frame285() {
  return (
    <div className="content-stretch flex gap-[10px] items-center justify-end relative shrink-0">
      <Frame69 />
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[32px] text-right text-white whitespace-nowrap">UAE</p>
    </div>
  );
}

function Group15() {
  return (
    <div className="h-[17.232px] relative shrink-0 w-[159.001px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 159 17.2315">
        <g id="Group 35110">
          <path d={svgPaths.p2e29b400} fill="var(--fill-0, white)" id="Vector" />
          <path d={svgPaths.p3126e500} fill="var(--fill-0, white)" id="Vector_2" />
          <path d={svgPaths.p26771a00} fill="var(--fill-0, white)" id="Vector_3" />
          <path d={svgPaths.p352cba80} fill="var(--fill-0, white)" id="Vector_4" />
        </g>
      </svg>
    </div>
  );
}

function Frame284() {
  return (
    <div className="content-stretch flex flex-col gap-[13px] items-start relative w-[460px]">
      <Frame285 />
      <div className="h-0 relative shrink-0 w-full">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 460 1">
            <line id="Line 53" stroke="var(--stroke-0, white)" x2="460" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <Group15 />
    </div>
  );
}

function Map() {
  return (
    <div className="h-[2821.228px] overflow-clip relative w-[3466.665px]" data-name="map">
      <div className="absolute inset-[45.78%_55.61%_19.42%_20.35%]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 834.433 982.696">
          <path d={svgPaths.p2d4aec00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <div className="absolute inset-[13.98%_79.57%_69.11%_0.31%]" data-name="Vector">
        <div className="absolute inset-[-0.1%_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 698.788 477.888">
            <path d={svgPaths.p10acf500} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[21.29%_82.77%_77.95%_16.5%]" data-name="Vector">
        <div className="absolute inset-[-2.31%_-1.99%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 26.1841 22.6127">
            <path d={svgPaths.p1ab7a700} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[22.21%_79.58%_77.5%_19.88%]" data-name="Vector">
        <div className="absolute inset-[-6.02%_-2.69%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 19.6176 9.31091">
            <path d={svgPaths.p1ce44eb0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[21.56%_81.57%_78.04%_18.16%]" data-name="Vector">
        <div className="absolute inset-[-4.48%_-5.33%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 10.3813 12.157">
            <path d={svgPaths.pe23100} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[20.01%_79.59%_79.5%_19.94%]" data-name="Vector">
        <div className="absolute inset-[-3.55%_-3.06%_-3.56%_-3.06%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 17.3487 15.0668">
            <path d={svgPaths.p7df0ae0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[26.42%_79.91%_71.17%_16.38%]" data-name="Vector">
        <div className="absolute inset-[-0.74%_-0.39%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 129.547 68.8981">
            <path d={svgPaths.p11d202f2} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[15.31%_65.04%_82.59%_30.27%]" data-name="Vector">
        <div className="absolute inset-[-0.84%_-0.31%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 163.655 60.4297">
            <path d={svgPaths.p7327000} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[15.03%_64.12%_84.15%_32.87%]" data-name="Vector">
        <div className="absolute inset-[-2.17%_-0.48%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 105.205 24.0341">
            <path d={svgPaths.p27d7b580} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[81.37%_11.25%_16.19%_87.07%]" data-name="Vector">
        <div className="absolute inset-[-0.73%_-0.86%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 59.4319 69.801">
            <path d={svgPaths.p1f805d80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[80.27%_12.61%_18.46%_86.73%]" data-name="Vector">
        <div className="absolute inset-[-1.4%_-2.16%_-1.4%_-2.17%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 24.1069 36.8075">
            <path d={svgPaths.p3f8f00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[83.28%_12.72%_13.73%_84.51%]" data-name="Vector">
        <div className="absolute inset-[-0.59%_-0.52%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 97.1301 85.4628">
            <path d={svgPaths.p2e82bd00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[86.32%_14.94%_13.15%_84.83%]" data-name="Vector">
        <div className="absolute inset-[-3.36%_-6.25%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.0035 15.8743">
            <path d={svgPaths.pbc25600} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[69.62%_55.93%_23.92%_41.47%]" data-name="Vector">
        <div className="absolute inset-[-0.27%_-0.56%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 90.9393 183.383">
            <path d={svgPaths.p2381c80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[73.73%_54.01%_25.91%_45.68%]" data-name="Vector">
        <div className="absolute inset-[-4.99%_-4.55%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 11.9823 11.0193">
            <path d={svgPaths.p11693900} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[73.39%_53.39%_26.31%_46.48%]" data-name="Vector">
        <div className="absolute inset-[-5.91%_-10.85%_-5.88%_-10.86%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 5.60662 9.49065">
            <path d={svgPaths.p2ba95a80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[83.28%_21.71%_15.26%_76.94%]" data-name="Vector">
        <div className="absolute inset-[-1.22%_-1.07%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 47.7906 42.0824">
            <path d={svgPaths.p3b2ba480} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[82.82%_23.23%_16.87%_76.63%]" data-name="Vector">
        <div className="absolute inset-[-5.83%_-10.39%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 5.81227 9.57551">
            <path d={svgPaths.p31bf76a0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[82.87%_21.78%_16.7%_78.02%]" data-name="Vector">
        <div className="absolute inset-[-4.11%_-7.18%_-4.11%_-7.19%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 7.96428 13.1648">
            <path d={svgPaths.p15967500} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[57.6%_54.49%_42.17%_45.05%]" data-name="Vector">
        <div className="absolute inset-[-7.77%_-3.1%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 17.1217 7.43279">
            <path d={svgPaths.p1b5fff00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[73.36%_15.26%_25.41%_83.62%]" data-name="Vector">
        <div className="absolute inset-[-1.44%_-1.28%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 40.1165 35.7715">
            <path d={svgPaths.p271af680} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[73.68%_15.08%_26.02%_84.73%]" data-name="Vector">
        <div className="absolute inset-[-5.98%_-7.9%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 7.33169 9.36049">
            <path d={svgPaths.p225fd900} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[74.02%_14.84%_25.75%_84.98%]" data-name="Vector">
        <div className="absolute inset-[-7.82%_-8.14%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 7.14567 7.39575">
            <path d={svgPaths.p1fe90000} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[72.06%_11.18%_27.41%_88.32%]" data-name="Vector">
        <div className="absolute inset-[-3.37%_-2.88%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18.3377 15.8341">
            <path d={svgPaths.p7f49580} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[71.59%_10.77%_28.07%_88.77%]" data-name="Vector">
        <div className="absolute inset-[-5.19%_-3.11%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 17.0918 10.6311">
            <path d={svgPaths.p1e2da120} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[72.83%_11.19%_26.98%_88.57%]" data-name="Vector">
        <div className="absolute inset-[-9.42%_-6.22%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.03907 6.31021">
            <path d={svgPaths.p317c6600} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[71.74%_11.56%_27.94%_88.23%]" data-name="Vector">
        <div className="absolute inset-[-5.44%_-6.65%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 8.52165 10.1995">
            <path d={svgPaths.p2c27cb00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[72.36%_10.91%_27.52%_89.01%]" data-name="Vector">
        <div className="absolute inset-[-14.61%_-18.9%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 3.64526 4.42133">
            <path d={svgPaths.p16a72f80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[72.04%_10.91%_27.88%_89.02%]" data-name="Vector">
        <div className="absolute inset-[-23.11%_-19.9%_-23.12%_-19.9%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 3.51242 3.16287">
            <path d={svgPaths.pc78a300} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[72.66%_10.78%_27.24%_89.15%]" data-name="Vector">
        <div className="absolute inset-[-17.16%_-22.59%_-17.18%_-22.59%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 3.21294 3.9147">
            <path d={svgPaths.p2f086400} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[72.94%_10.79%_26.95%_89.12%]" data-name="Vector">
        <div className="absolute inset-[-16.61%_-17.39%_-16.62%_-17.39%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 3.87477 4.00994">
            <path d={svgPaths.p264b6b00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[73.55%_15.35%_26.24%_84.52%]" data-name="Vector">
        <div className="absolute inset-[-8.24%_-11.91%_-8.24%_-11.92%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 5.19607 7.06604">
            <path d={svgPaths.p3da6bd80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[73.41%_14.25%_26.51%_85.65%]" data-name="Vector">
        <div className="absolute inset-[-21.7%_-14.7%_-21.72%_-14.69%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 4.40335 3.30506">
            <path d={svgPaths.p2fe6af00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[73%_14.42%_26.78%_85.48%]" data-name="Vector">
        <div className="absolute inset-[-8.35%_-13.21%_-8.36%_-13.19%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 4.78501 6.98441">
            <path d={svgPaths.p37566080} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[72.68%_14.44%_27.1%_85.4%]" data-name="Vector">
        <div className="absolute inset-[-7.98%_-8.95%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 6.58832 7.26661">
            <path d={svgPaths.p19df37f1} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[72.14%_14.71%_27.65%_85.1%]" data-name="Vector">
        <div className="absolute inset-[-8.17%_-7.77%_-8.2%_-7.77%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 7.43904 7.12267">
            <path d={svgPaths.pac339c0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[70.93%_15.18%_28.72%_84.59%]" data-name="Vector">
        <div className="absolute inset-[-5.16%_-6.19%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.07337 10.6978">
            <path d={svgPaths.p5050300} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[71.37%_15.13%_28.5%_84.77%]" data-name="Vector">
        <div className="absolute inset-[-13.38%_-15.21%_-13.37%_-15.2%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 4.29038 4.73599">
            <path d={svgPaths.p3a53b880} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[71.53%_15%_28.3%_84.87%]" data-name="Vector">
        <div className="absolute inset-[-10.16%_-11.34%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 5.40848 5.92214">
            <path d={svgPaths.p28f4fa00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[70.76%_15.34%_29.05%_84.54%]" data-name="Vector">
        <div className="absolute inset-[-9.3%_-12.18%_-9.3%_-12.15%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 5.10409 6.37885">
            <path d={svgPaths.p5f2c700} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[70.96%_14.7%_28.02%_84.98%]" data-name="Vector">
        <div className="absolute inset-[-1.74%_-4.45%_-1.74%_-4.44%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12.2576 29.7269">
            <path d={svgPaths.p13a74d00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[81.07%_21.05%_18.93%_78.95%]" data-name="Vector">
        <div className="absolute inset-[-199.55%_-0.5px_0_-0.5px]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1 0.750569">
            <path d={svgPaths.peb31d00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[68.9%_19.92%_17.52%_66.01%]" data-name="Vector">
        <div className="absolute inset-[-0.13%_-0.1%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 488.912 384.304">
            <path d={svgPaths.p3b785200} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[69.15%_27.67%_30.49%_71.81%]" data-name="Vector">
        <div className="absolute inset-[-4.85%_-2.78%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18.9984 11.3005">
            <path d={svgPaths.pe565680} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[80.88%_25.38%_18.87%_74.09%]" data-name="Vector">
        <div className="absolute inset-[-7.03%_-2.74%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 19.2811 8.11703">
            <path d={svgPaths.p21730a80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[60.91%_36.53%_33.38%_59.62%]" data-name="Vector">
        <div className="absolute inset-[-0.31%_-0.38%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 134.308 162.134">
            <path d={svgPaths.p206dfe00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[75.99%_33.81%_23.58%_65.96%]" data-name="Vector">
        <div className="absolute inset-[-4.17%_-6.26%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 8.98219 12.9902">
            <path d={svgPaths.p21559500} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[76.1%_33.98%_23.41%_65.84%]" data-name="Vector">
        <div className="absolute inset-[-3.65%_-8.39%_-3.65%_-8.38%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 6.96624 14.7101">
            <path d={svgPaths.p7645b40} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[73.53%_33.21%_26.17%_66.65%]" data-name="Vector">
        <div className="absolute inset-[-6%_-10.07%_-6%_-10.08%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 5.95899 9.33027">
            <path d={svgPaths.pf8b3900} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[70.29%_25.74%_29.34%_74.04%]" data-name="Vector">
        <div className="absolute inset-[-4.84%_-6.43%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 8.77139 11.3236">
            <path d={svgPaths.p3e6a400} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[71.61%_24.8%_28.24%_74.99%]" data-name="Vector">
        <div className="absolute inset-[-11.73%_-6.79%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 8.36772 5.26429">
            <path d={svgPaths.p1bb15170} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[58.97%_44.92%_39.12%_54.19%]" data-name="Vector">
        <div className="absolute inset-[-0.92%_-1.63%_-0.93%_-1.63%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 31.751 55.0595">
            <path d={svgPaths.pfda3e80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[63.86%_20.96%_31.11%_72%]" data-name="Vector">
        <div className="absolute inset-[-0.35%_-0.2%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 245.099 142.709">
            <path d={svgPaths.p3eeb6f00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[65.75%_20.41%_33.24%_78.21%]" data-name="Vector">
        <div className="absolute inset-[-1.76%_-1.04%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 48.8471 29.4577">
            <path d={svgPaths.p11d8f440} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[64.89%_20.14%_33.89%_78.78%]" data-name="Vector">
        <div className="absolute inset-[-1.45%_-1.34%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 38.3073 35.4282">
            <path d={svgPaths.pc3fd00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[64.64%_22.07%_35.1%_77.55%]" data-name="Vector">
        <div className="absolute inset-[-6.99%_-3.86%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 13.9603 8.15064">
            <path d={svgPaths.p27eb1780} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[66.11%_19.15%_32.85%_80.38%]" data-name="Vector">
        <div className="absolute inset-[-1.71%_-3.04%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 17.4687 30.2755">
            <path d={svgPaths.p654fc00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[66.9%_18.45%_32.63%_81.03%]" data-name="Vector">
        <div className="absolute inset-[-3.79%_-2.75%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 19.1871 14.1824">
            <path d={svgPaths.pd809700} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[67.29%_17.77%_32.13%_81.68%]" data-name="Vector">
        <div className="absolute inset-[-3.02%_-2.6%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20.2063 17.5755">
            <path d={svgPaths.pc9c3080} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[67.71%_17.15%_31.58%_82.52%]" data-name="Vector">
        <div className="absolute inset-[-2.51%_-4.32%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12.5814 20.93">
            <path d={svgPaths.p23277c00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[68.17%_17.39%_31.46%_82.13%]" data-name="Vector">
        <div className="absolute inset-[-4.74%_-3.03%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 17.5153 11.5514">
            <path d={svgPaths.p2a7abfc0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[68.64%_16.89%_31%_82.68%]" data-name="Vector">
        <div className="absolute inset-[-4.93%_-3.39%_-4.95%_-3.39%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 15.7583 11.0984">
            <path d={svgPaths.p396d3400} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[67.35%_18.33%_31.97%_81.02%]" data-name="Vector">
        <div className="absolute inset-[-2.61%_-2.24%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 23.3359 20.1819">
            <path d={svgPaths.p24620d80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[60.12%_31.94%_34.26%_64.45%]" data-name="Vector">
        <div className="absolute inset-[-0.32%_-0.4%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 126.046 159.596">
            <path d={svgPaths.p10b1ab10} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[64.43%_36.27%_34.76%_63.17%]" data-name="Vector">
        <div className="absolute inset-[-2.18%_-2.56%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20.5171 23.9284">
            <path d={svgPaths.p16f78580} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[64.95%_35.75%_34.73%_63.95%]" data-name="Vector">
        <div className="absolute inset-[-5.47%_-4.75%_-5.46%_-4.75%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 11.5317 10.1521">
            <path d={svgPaths.p3ec7d100} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[62.29%_39.88%_37.38%_59.84%]" data-name="Vector">
        <div className="absolute inset-[-5.36%_-5.06%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 10.8813 10.3219">
            <path d={svgPaths.p1007b2c0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[63%_39.36%_36.51%_60.33%]" data-name="Vector">
        <div className="absolute inset-[-3.62%_-4.68%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 11.6877 14.8026">
            <path d={svgPaths.p22955400} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[64.19%_38.89%_35.4%_60.86%]" data-name="Vector">
        <div className="absolute inset-[-4.35%_-5.95%_-4.35%_-5.94%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.40286 12.4981">
            <path d={svgPaths.p36e91600} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[63.71%_39.11%_35.93%_60.72%]" data-name="Vector">
        <div className="absolute inset-[-4.83%_-8.09%_-4.83%_-8.08%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 7.18282 11.3441">
            <path d={svgPaths.p99f940} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[64.69%_38.49%_34.64%_61.16%]" data-name="Vector">
        <div className="absolute inset-[-2.65%_-4.14%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 13.0741 19.8884">
            <path d={svgPaths.pfdd0b80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[66.56%_33.17%_31.99%_63.29%]" data-name="Vector">
        <div className="absolute inset-[-1.22%_-0.41%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 123.798 42.0135">
            <path d={svgPaths.p355fe200} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[67.69%_32.79%_31.96%_66.92%]" data-name="Vector">
        <div className="absolute inset-[-4.96%_-4.95%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 11.1093 11.0888">
            <path d={svgPaths.p37c68200} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[67.59%_31.96%_31.89%_67.33%]" data-name="Vector">
        <div className="absolute inset-[-3.41%_-2.03%_-3.42%_-2.03%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 25.6143 15.6228">
            <path d={svgPaths.p319c4b00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[68.2%_31.4%_31.25%_67.98%]" data-name="Vector">
        <div className="absolute inset-[-3.22%_-2.34%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 22.37 16.5371">
            <path d={svgPaths.p27f3ed80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[67.69%_30.97%_31.92%_68.2%]" data-name="Vector">
        <div className="absolute inset-[-4.56%_-1.75%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 29.5251 11.9626">
            <path d={svgPaths.p22dab380} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[67.61%_29.94%_32.02%_69.2%]" data-name="Vector">
        <div className="absolute inset-[-4.88%_-1.67%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 30.8748 11.2547">
            <path d={svgPaths.p39970100} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[67.34%_29.31%_32.4%_70.29%]" data-name="Vector">
        <div className="absolute inset-[-6.92%_-3.6%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 14.8885 8.2283">
            <path d={svgPaths.p36ad6b80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[67.72%_29.15%_30.96%_69.29%]" data-name="Vector">
        <div className="absolute inset-[-1.34%_-0.93%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 55.0451 38.2378">
            <path d={svgPaths.p1f878cc0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[67.16%_27.56%_32.25%_72.03%]" data-name="Vector">
        <div className="absolute inset-[-3.01%_-3.58%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 14.9826 17.6389">
            <path d={svgPaths.p2b86b900} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[66.34%_26.49%_32.87%_73.19%]" data-name="Vector">
        <div className="absolute inset-[-2.23%_-4.45%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12.246 23.3972">
            <path d={svgPaths.p3f4f0480} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[62.83%_29.81%_33.46%_67.86%]" data-name="Vector">
        <div className="absolute inset-[-0.48%_-0.62%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 81.6704 105.433">
            <path d={svgPaths.p134d8e00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[64.33%_30.38%_35.3%_69.32%]" data-name="Vector">
        <div className="absolute inset-[-4.78%_-4.74%_-4.78%_-4.73%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 11.5705 11.4667">
            <path d={svgPaths.p29462300} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[65.93%_30.53%_33.52%_69.16%]" data-name="Vector">
        <div className="absolute inset-[-3.18%_-4.68%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 11.6903 16.7384">
            <path d={svgPaths.p3931800} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[64.48%_29.54%_35.19%_69.82%]" data-name="Vector">
        <div className="absolute inset-[-5.24%_-2.27%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 23.0414 10.5488">
            <path d={svgPaths.p10903180} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[65.18%_29.15%_34.37%_70.41%]" data-name="Vector">
        <div className="absolute inset-[-3.95%_-3.29%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16.1966 13.6452">
            <path d={svgPaths.pd45c170} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[65.04%_27.85%_34.37%_70.99%]" data-name="Vector">
        <div className="absolute inset-[-3.02%_-1.24%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 41.2199 17.5555">
            <path d={svgPaths.p26de1300} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[64.55%_28.03%_35.28%_71.67%]" data-name="Vector">
        <div className="absolute inset-[-10.45%_-4.87%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 11.2656 5.7854">
            <path d={svgPaths.p3a2e0000} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[64.03%_25.93%_35.64%_73.65%]" data-name="Vector">
        <div className="absolute inset-[-5.35%_-3.49%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 15.3122 10.3388">
            <path d={svgPaths.p3198dcc0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[64.48%_25.9%_35.34%_73.63%]" data-name="Vector">
        <div className="absolute inset-[-10.11%_-3.08%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 17.2131 5.94724">
            <path d={svgPaths.p2b387e00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[63.7%_27.7%_36%_71.92%]" data-name="Vector">
        <div className="absolute inset-[-5.94%_-3.72%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 14.4521 9.42524">
            <path d={svgPaths.p1e646d80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[64.31%_28.86%_35.37%_70.9%]" data-name="Vector">
        <div className="absolute inset-[-5.51%_-5.91%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.45755 10.0757">
            <path d={svgPaths.p1973c800} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[62.49%_28.62%_37.22%_71.13%]" data-name="Vector">
        <div className="absolute inset-[-6.01%_-5.88%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.50283 9.31555">
            <path d={svgPaths.p2fdd580} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[62.81%_28.91%_36.7%_70.88%]" data-name="Vector">
        <div className="absolute inset-[-3.58%_-6.76%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 8.39719 14.98">
            <path d={svgPaths.p2e309ab0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[63%_28.57%_35.79%_70.86%]" data-name="Vector">
        <div className="absolute inset-[-1.46%_-2.53%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20.7312 35.247">
            <path d={svgPaths.p1020c080} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[57.73%_31.53%_40.25%_67.3%]" data-name="Vector">
        <div className="absolute inset-[-0.88%_-1.23%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 41.4888 57.9997">
            <path d={svgPaths.p36e1c700} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[61.51%_29.25%_38.02%_70.62%]" data-name="Vector">
        <div className="absolute inset-[-3.78%_-11.29%_-3.78%_-11.28%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 5.43074 14.2168">
            <path d={svgPaths.p30d97800} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[60.46%_30.87%_39.35%_68.96%]" data-name="Vector">
        <div className="absolute inset-[-9.67%_-8.3%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 7.02772 6.17098">
            <path d={svgPaths.p2998af00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[60.78%_31.14%_38.86%_68.55%]" data-name="Vector">
        <div className="absolute inset-[-5.02%_-4.74%_-5.02%_-4.75%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 11.5457 10.9591">
            <path d={svgPaths.p7fb5e00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[61.13%_31.58%_38.5%_68.21%]" data-name="Vector">
        <div className="absolute inset-[-4.76%_-6.92%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 8.22566 11.4952">
            <path d={svgPaths.p164c5600} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[58.91%_29.31%_38.95%_69.06%]" data-name="Vector">
        <div className="absolute inset-[-0.83%_-0.89%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 57.4068 61.3318">
            <path d={svgPaths.p4e3170} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[57.2%_31.11%_42.13%_68.42%]" data-name="Vector">
        <div className="absolute inset-[-2.66%_-3.06%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 17.3416 19.7704">
            <path d={svgPaths.pad6ef00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[57.97%_30.53%_41.29%_68.98%]" data-name="Vector">
        <div className="absolute inset-[-2.4%_-2.98%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 17.7696 21.8197">
            <path d={svgPaths.p38eff300} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[54.72%_30.14%_42.47%_68.21%]" data-name="Vector">
        <div className="absolute inset-[-0.63%_-0.88%_-0.63%_-0.87%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 58.2729 80.1379">
            <path d={svgPaths.p1c734000} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[58.47%_30.43%_40.64%_69.19%]" data-name="Vector">
        <div className="absolute inset-[-1.99%_-3.84%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 14.0142 26.0829">
            <path d={svgPaths.p31a3900} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[58.83%_30.08%_40.84%_69.66%]" data-name="Vector">
        <div className="absolute inset-[-5.31%_-5.6%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.93313 10.4091">
            <path d={svgPaths.p20939800} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[58.22%_29.82%_41.18%_69.84%]" data-name="Vector">
        <div className="absolute inset-[-2.95%_-4.32%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12.5787 17.9592">
            <path d={svgPaths.p170ba900} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[57.65%_29.67%_41.65%_69.85%]" data-name="Vector">
        <div className="absolute inset-[-2.51%_-3%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 17.6684 20.9147">
            <path d={svgPaths.pd470100} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[57.72%_30.24%_41.93%_69.42%]" data-name="Vector">
        <div className="absolute inset-[-5.11%_-4.26%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12.7456 10.7872">
            <path d={svgPaths.p7ca1380} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[58.27%_30.26%_40.99%_69.55%]" data-name="Vector">
        <div className="absolute inset-[-2.39%_-7.53%_-2.39%_-7.54%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 7.63445 21.9563">
            <path d={svgPaths.p35ee100} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[51.54%_30.96%_46.8%_68.34%]" data-name="Vector">
        <div className="absolute inset-[-1.07%_-2.05%_-1.07%_-2.04%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 25.4575 47.7726">
            <path d={svgPaths.p23d289c0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[43.29%_27.55%_54.94%_71.61%]" data-name="Vector">
        <div className="absolute inset-[-1%_-1.72%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 30.1236 50.8922">
            <path d={svgPaths.p5014b00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[43.05%_26.54%_55.91%_72.63%]" data-name="Vector">
        <div className="absolute inset-[-1.71%_-1.73%_-1.7%_-1.73%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 29.8488 30.3166">
            <path d={svgPaths.p1f9a3080} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[38.78%_23.98%_56.35%_72.14%]" data-name="Vector">
        <div className="absolute inset-[-0.36%_-0.37%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 135.561 138.196">
            <path d={svgPaths.p1b0d6700} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[36.23%_22.77%_61.25%_75.21%]" data-name="Vector">
        <div className="absolute inset-[-0.7%_-0.71%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 70.9709 72.1115">
            <path d={svgPaths.p3de6a900} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[30.84%_23.17%_64.02%_75.87%]" data-name="Vector">
        <div className="absolute inset-[-0.35%_-1.51%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 34.0867 145.791">
            <path d={svgPaths.p2883dc00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[20.62%_76.29%_78.99%_23.21%]" data-name="Vector">
        <div className="absolute inset-[-4.61%_-2.93%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18.0879 11.8367">
            <path d={svgPaths.p21174580} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[25.98%_75.78%_73.34%_23.81%]" data-name="Vector">
        <div className="absolute inset-[-2.58%_-3.47%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 15.4004 20.3547">
            <path d={svgPaths.p30eade00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[26.94%_73.8%_72.38%_25.86%]" data-name="Vector">
        <div className="absolute inset-[-2.59%_-4.33%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12.5585 20.3104">
            <path d={svgPaths.p2fb94080} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[30.25%_75.43%_67.32%_22.79%]" data-name="Vector">
        <div className="absolute inset-[-0.73%_-0.81%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 62.6832 69.751">
            <path d={svgPaths.p138f1600} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[28.37%_75.7%_70.57%_23.76%]" data-name="Vector">
        <div className="absolute inset-[-1.67%_-2.72%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 19.3941 30.9838">
            <path d={svgPaths.p25f66400} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[28.28%_72.9%_66.46%_24.15%]" data-name="Vector">
        <div className="absolute inset-[-0.34%_-0.49%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 103.214 149.507">
            <path d={svgPaths.p591f580} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[30.81%_75.05%_68.83%_24.72%]" data-name="Vector">
        <div className="absolute inset-[-4.89%_-6.09%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.21259 11.2341">
            <path d={svgPaths.p3cbe3a00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[27.76%_74.44%_71.74%_25.27%]" data-name="Vector">
        <div className="absolute inset-[-3.53%_-5.11%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 10.7941 15.1566">
            <path d={svgPaths.p2b5f1e00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[17.1%_49.55%_78.87%_44.29%]" data-name="Vector">
        <div className="absolute inset-[-0.44%_-0.23%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 214.402 114.545">
            <path d={svgPaths.p1dc1f7c0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[21.66%_56.03%_77.76%_43.26%]" data-name="Vector">
        <div className="absolute inset-[-3.02%_-2.03%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 25.6762 17.5481">
            <path d={svgPaths.p1b748f0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[14.8%_56.68%_84.83%_42.19%]" data-name="Vector">
        <div className="absolute inset-[-4.9%_-1.27%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 40.244 11.2018">
            <path d={svgPaths.p17ccadf0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[14.67%_55.62%_84.6%_43.17%]" data-name="Vector">
        <div className="absolute inset-[-2.41%_-1.19%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 43.0886 21.721">
            <path d={svgPaths.pfc08800} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[15.25%_55.63%_84.5%_43.69%]" data-name="Vector">
        <div className="absolute inset-[-7.22%_-2.13%_-7.21%_-2.13%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 24.4688 7.92003">
            <path d={svgPaths.p13b2e400} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[14.59%_50.85%_84.91%_48.29%]" data-name="Vector">
        <div className="absolute inset-[-3.59%_-1.7%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 30.4799 14.9428">
            <path d={svgPaths.p390362e0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[14.64%_51.89%_84.76%_47.13%]" data-name="Vector">
        <div className="absolute inset-[-2.96%_-1.47%_-2.96%_-1.48%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 34.9091 17.9031">
            <path d={svgPaths.p175d6800} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[14.99%_53.12%_84.65%_45.91%]" data-name="Vector">
        <div className="absolute inset-[-4.95%_-1.49%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 34.4942 11.1047">
            <path d={svgPaths.p3b3ed900} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[14.12%_52.8%_84.96%_45.31%]" data-name="Vector">
        <div className="absolute inset-[-1.94%_-0.76%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 66.4638 26.8051">
            <path d={svgPaths.p18424380} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[14.19%_51.27%_85.51%_48.07%]" data-name="Vector">
        <div className="absolute inset-[-5.87%_-2.19%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 23.7936 9.51376">
            <path d={svgPaths.pcf3d00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[14.96%_54.21%_84.68%_44.67%]" data-name="Vector">
        <div className="absolute inset-[-4.96%_-1.3%_-4.96%_-1.29%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 39.602 11.0736">
            <path d={svgPaths.pa18bc00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[15.66%_36.71%_83.33%_61.08%]" data-name="Vector">
        <div className="absolute inset-[-1.76%_-0.65%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 77.6146 29.4031">
            <path d={svgPaths.p3f660a00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[14.55%_39.38%_84.24%_58.16%]" data-name="Vector">
        <div className="absolute inset-[-1.46%_-0.59%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 86.2663 35.3504">
            <path d={svgPaths.pc4ff600} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[15.24%_38.63%_83.91%_59.21%]" data-name="Vector">
        <div className="absolute inset-[-2.08%_-0.67%_-2.07%_-0.67%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 75.885 25.1075">
            <path d={svgPaths.p1de95000} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[14.65%_45.52%_85.05%_53.94%]" data-name="Vector">
        <div className="absolute inset-[-5.9%_-2.7%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 19.5171 9.47682">
            <path d={svgPaths.p3be53200} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[15.45%_46.5%_84.32%_52.94%]" data-name="Vector">
        <div className="absolute inset-[-7.75%_-2.58%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20.3607 7.4539">
            <path d={svgPaths.p1a806700} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[17%_39.92%_82.52%_59.31%]" data-name="Vector">
        <div className="absolute inset-[-3.75%_-1.87%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 27.6722 14.3487">
            <path d={svgPaths.p39009a00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[16.31%_36.06%_83.45%_63.48%]" data-name="Vector">
        <div className="absolute inset-[-7.41%_-3.18%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16.7356 7.74859">
            <path d={svgPaths.pa228880} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[18.63%_34.06%_81.12%_65.42%]" data-name="Vector">
        <div className="absolute inset-[-7.05%_-2.76%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 19.121 8.09688">
            <path d={svgPaths.p2e3a9f80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[17.85%_26.02%_81.82%_73.72%]" data-name="Vector">
        <div className="absolute inset-[-5.43%_-5.36%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 10.325 10.2034">
            <path d={svgPaths.p1a3b6000} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[18.75%_25.98%_80.91%_73.65%]" data-name="Vector">
        <div className="absolute inset-[-5.22%_-3.87%_-5.22%_-3.84%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 14.0101 10.5836">
            <path d={svgPaths.p1c2f7600} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[18.76%_24.32%_80.92%_75.33%]" data-name="Vector">
        <div className="absolute inset-[-5.65%_-4.12%_-5.66%_-4.12%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 13.1324 9.84736">
            <path d={svgPaths.p39d2900} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[19.04%_23.4%_80.49%_75.2%]" data-name="Vector">
        <div className="absolute inset-[-3.76%_-1.03%_-3.77%_-1.03%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 49.5483 14.2751">
            <path d={svgPaths.p155d5480} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[17.57%_22.84%_81.42%_74.24%]" data-name="Vector">
        <div className="absolute inset-[-1.76%_-0.49%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 102.351 29.3496">
            <path d={svgPaths.p386d13c0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[30.36%_25.34%_69.25%_74.37%]" data-name="Vector">
        <div className="absolute inset-[-4.56%_-5.03%_-4.56%_-5.02%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 10.9608 11.9679">
            <path d={svgPaths.p25e067d0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[30.35%_25.68%_69.43%_74.12%]" data-name="Vector">
        <div className="absolute inset-[-7.75%_-7.31%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 7.83561 7.45168">
            <path d={svgPaths.p36759600} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[30.82%_25.45%_68.96%_74.32%]" data-name="Vector">
        <div className="absolute inset-[-8.19%_-6.37%_-8.19%_-6.36%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 8.8523 7.10637">
            <path d={svgPaths.p3a7cc280} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[40.71%_68.18%_58.34%_30.75%]" data-name="Vector">
        <div className="absolute inset-[-1.87%_-1.35%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 38.1007 27.8054">
            <path d={svgPaths.p3dc53100} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[37.93%_70.22%_61.26%_29.43%]" data-name="Vector">
        <div className="absolute inset-[-2.18%_-4.11%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 13.1567 23.9882">
            <path d={svgPaths.p8931200} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[38.87%_70.08%_59.67%_29.28%]" data-name="Vector">
        <div className="absolute inset-[-1.21%_-2.28%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 22.9036 42.1799">
            <path d={svgPaths.p152a3600} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[39.63%_72.35%_59.94%_27.28%]" data-name="Vector">
        <div className="absolute inset-[-4.15%_-3.88%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 13.8748 13.0386">
            <path d={svgPaths.p1a066c00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[39.52%_72.03%_60.22%_27.75%]" data-name="Vector">
        <div className="absolute inset-[-6.69%_-6.54%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 8.65077 8.46948">
            <path d={svgPaths.p3437e600} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[40.08%_72.96%_59.54%_26.84%]" data-name="Vector">
        <div className="absolute inset-[-4.62%_-7.28%_-4.62%_-7.27%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 7.87206 11.8154">
            <path d={svgPaths.p48c6d00} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[16.68%_7.06%_36.95%_23.16%]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 2419.92 1309.01">
          <path d={svgPaths.pf5bfbf0} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <div className="absolute flex h-[174.407px] items-center justify-center left-[854.72px] top-[920.66px] w-[169.732px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
        <div className="flex-none rotate-[-8.05deg]">
          <div className="h-[155px] relative w-[149.5px]">
            <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 149.5 155">
              <path d={svgPaths.p16cf1a00} fill="var(--fill-0, white)" id="Vector 147" />
            </svg>
          </div>
        </div>
      </div>
      <div className="absolute flex h-[64.056px] items-center justify-center left-[1535.43px] top-[1350.29px] w-[72.135px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
        <div className="flex-none rotate-[-8.05deg]">
          <div className="h-[55.5px] relative w-[65.004px]">
            <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 65.0039 55.5">
              <path d={svgPaths.p3a22d080} fill="var(--fill-0, white)" id="Vector 148" />
            </svg>
          </div>
        </div>
      </div>
      <div className="absolute flex h-[141.795px] items-center justify-center left-[921.09px] top-[893.88px] w-[460.589px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "113" } as React.CSSProperties}>
        <div className="flex-none rotate-[-8.05deg]">
          <Frame283 />
        </div>
      </div>
      <div className="absolute flex h-[136.924px] items-center justify-center left-[1100.75px] top-[1356.45px] w-[465.722px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "75" } as React.CSSProperties}>
        <div className="flex-none rotate-[-8.05deg]">
          <Frame284 />
        </div>
      </div>
    </div>
  );
}

function Frame176() {
  return (
    <div className="absolute content-stretch flex flex-col h-[304px] items-start left-[60px] top-[284px] w-[764px]">
      <div className="font-['Geist:ExtraLight',sans-serif] font-extralight h-[568px] leading-[0] relative shrink-0 text-[#f2f2f2] text-[0px] w-full whitespace-pre-wrap">
        <p className="mb-0 text-[40px]">
          <span className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2]">
            Tete de Group a Abu Dhabi, ADGM
            <br aria-hidden="true" />
            <br aria-hidden="true" />
          </span>
          <span className="leading-[1.2]">The total underlying private asset market exceeds $300–400 trillion.</span>
        </p>
        <p className="leading-[1.2] text-[40px]">Only a fraction will be tokenized over the next decade.</p>
      </div>
    </div>
  );
}

function CreatableInvestmentPitchTemplate4() {
  return (
    <div className="bg-[#1e1c1b] h-[1080px] overflow-clip relative shrink-0 w-[1920px]" data-name="Creatable Investment Pitch Template | 33">
      <div className="absolute h-[1277px] left-[2947.5px] top-[1565px] w-[1079px]">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 32 32">
          <g id="Rectangle 4206" />
        </svg>
      </div>
      <div className="absolute content-stretch flex flex-col gap-[48px] items-start left-0 p-[60px] top-0 w-[1920px]" data-name="Titre">
        <Frame24 />
        <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[60px] text-white w-full">Licences</p>
        <Frame144 />
      </div>
      <div className="absolute flex h-[3278.868px] items-center justify-center left-[-131px] top-[-809px] w-[3827.565px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "3188" } as React.CSSProperties}>
        <div className="flex-none rotate-[8.05deg]">
          <Map />
        </div>
      </div>
      <Frame176 />
      <p className="absolute font-['Neue_Haas_Grotesk_Display_Pro:45_Light',sans-serif] leading-[normal] left-[60px] not-italic text-[150px] text-white top-[752px] whitespace-nowrap">XX</p>
      <p className="absolute font-['Neue_Haas_Grotesk_Display_Pro:45_Light',sans-serif] leading-[normal] left-[60px] not-italic text-[26px] text-white top-[931px] w-[222px]">Lorem ipsum dolor</p>
      <p className="absolute font-['Neue_Haas_Grotesk_Display_Pro:45_Light',sans-serif] leading-[normal] left-[308px] not-italic text-[150px] text-white top-[752px] whitespace-nowrap">XX</p>
      <p className="absolute font-['Neue_Haas_Grotesk_Display_Pro:45_Light',sans-serif] leading-[normal] left-[308px] not-italic text-[26px] text-white top-[931px] whitespace-nowrap">Lorem ipsum dolor</p>
    </div>
  );
}

function Logo15() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame25() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo15 />
    </div>
  );
}

function Frame70() {
  return (
    <div className="content-stretch flex gap-[16px] items-center justify-center relative shrink-0 w-full">
      <div className="flex h-[0.333px] items-center justify-center relative shrink-0 w-[34px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
        <div className="flex-none rotate-[-0.56deg]">
          <div className="h-0 relative w-[34.002px]">
            <div className="absolute inset-[-7.36px_-2.94%_-7.36px_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.0016 14.7279">
                <path d={svgPaths.p34bcc570} fill="var(--stroke-0, #1E1C1B)" id="Arrow 1" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">Sous titre ou phrase d’intro</p>
    </div>
  );
}

function Frame146() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1747 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="1747" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame99() {
  return (
    <div className="content-stretch flex items-center relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">Venerat auspiciis fulgorem primis atque foedere quo Rom.</p>
    </div>
  );
}

function Frame100() {
  return (
    <div className="content-stretch flex items-center relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[27px] whitespace-pre-wrap">{`Angustus levibus insontium angustus suae corpus ad et ad solet angustus  victoriam solet.`}</p>
    </div>
  );
}

function Frame271() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-start relative shrink-0 w-full">
      <p className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[40px] w-full">Lorem ipsum</p>
      <Frame99 />
      <Frame100 />
    </div>
  );
}

function Frame76() {
  return (
    <div className="absolute bg-white content-stretch flex flex-col items-center justify-center left-[44px] rounded-[30px] size-[60px] top-[-30px]">
      <div aria-hidden="true" className="absolute border-3 border-[#f2f2f2] border-solid inset-0 pointer-events-none rounded-[30px]" />
      <p className="font-['Merriweather_120pt:Black',sans-serif] leading-[1.2] not-italic relative shrink-0 text-[#4f46e5] text-[24px] text-center whitespace-nowrap">01</p>
    </div>
  );
}

function Frame212() {
  return (
    <div className="bg-[#f2f2f2] flex-[1_0_0] h-full min-h-px min-w-px relative rounded-[10px]">
      <div className="content-stretch flex flex-col items-start justify-between p-[60px] relative size-full">
        <Frame271 />
        <p className="font-['Geist:Light',sans-serif] font-light leading-[1.2] min-w-full relative shrink-0 text-[#8a8a8a] text-[24px] w-[min-content] whitespace-pre-wrap">{`Angustus levibus insontium angustus suae corpus ad et ad solet angustus  victoriam solet animus increpuisset victoriam quicquid tener quassari.`}</p>
        <Frame76 />
      </div>
    </div>
  );
}

function Frame249() {
  return (
    <div className="h-[45px] relative w-[33px]">
      <div className="absolute inset-[-4.07%_0_-4.82%_0]">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 33 49">
          <g id="Frame 2147238879">
            <path d={svgPaths.p3b425680} fill="var(--stroke-0, #8D857F)" id="Arrow 3" />
          </g>
        </svg>
      </div>
    </div>
  );
}

function Frame101() {
  return (
    <div className="content-stretch flex items-center relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">Venerat auspiciis fulgorem primis atque foedere quo Roma quarum perfectam in quo primis plerumque atque.</p>
    </div>
  );
}

function Frame102() {
  return (
    <div className="content-stretch flex items-center relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[27px] whitespace-pre-wrap">{`Angustus levibus insontium angustus suae corpus ad et ad solet angustus  victoriam solet animus increpuisset victoriam quicquid tener quassari.`}</p>
    </div>
  );
}

function Frame103() {
  return (
    <div className="absolute bg-white content-stretch flex flex-col items-center justify-center left-[44px] rounded-[30px] size-[60px] top-[-30px]">
      <div aria-hidden="true" className="absolute border-3 border-[#f2f2f2] border-solid inset-0 pointer-events-none rounded-[30px]" />
      <p className="font-['Merriweather_120pt:Black',sans-serif] leading-[1.2] not-italic relative shrink-0 text-[#4f46e5] text-[24px] text-center whitespace-nowrap">02</p>
    </div>
  );
}

function Frame213() {
  return (
    <div className="bg-[#f2f2f2] flex-[1_0_0] h-full min-h-px min-w-px relative rounded-[10px]">
      <div className="content-stretch flex flex-col gap-[24px] items-start p-[60px] relative size-full">
        <p className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-w-full relative shrink-0 text-[#1e1c1b] text-[40px] w-[min-content]">Lorem ipsum</p>
        <Frame101 />
        <Frame102 />
        <Frame103 />
      </div>
    </div>
  );
}

function Frame250() {
  return (
    <div className="h-[45px] relative w-[33px]">
      <div className="absolute inset-[-4.07%_0_-4.82%_0]">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 33 49">
          <g id="Frame 2147238879">
            <path d={svgPaths.p3b425680} fill="var(--stroke-0, #8D857F)" id="Arrow 3" />
          </g>
        </svg>
      </div>
    </div>
  );
}

function Frame104() {
  return (
    <div className="content-stretch flex items-center relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">Venerat auspiciis fulgorem primis atque.</p>
    </div>
  );
}

function Frame272() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-start relative shrink-0 w-full">
      <p className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[40px] w-full">Lorem ipsum</p>
      <Frame104 />
      <p className="font-['Geist:Light',sans-serif] font-light leading-[1.2] relative shrink-0 text-[#8a8a8a] text-[24px] w-full whitespace-pre-wrap">{`Angustus levibus insontium angustus suae corpus ad et ad solet angustus  victoriam solet animus increpuisset victoriam quicquid tener quassari.`}</p>
    </div>
  );
}

function Frame105() {
  return (
    <div className="content-stretch flex items-center relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[27px]">Angustus levibus insontium angustus suae.</p>
    </div>
  );
}

function Frame273() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-start relative shrink-0 w-full">
      <p className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[40px] w-full">Lorem ipsum</p>
      <p className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[32px] w-full">Venerat auspiciis fulgorem primis atque.</p>
      <Frame105 />
    </div>
  );
}

function Frame106() {
  return (
    <div className="absolute bg-white content-stretch flex flex-col items-center justify-center left-[44px] rounded-[30px] size-[60px] top-[-30px]">
      <div aria-hidden="true" className="absolute border-3 border-[#1e1c1b] border-solid inset-0 pointer-events-none rounded-[30px]" />
      <p className="font-['Merriweather_120pt:Black',sans-serif] leading-[1.2] not-italic relative shrink-0 text-[#4f46e5] text-[24px] text-center whitespace-nowrap">03</p>
    </div>
  );
}

function Frame214() {
  return (
    <div className="bg-white flex-[1_0_0] h-full min-h-px min-w-px relative rounded-[10px]">
      <div aria-hidden="true" className="absolute border-3 border-[#1e1c1b] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <div className="content-stretch flex flex-col items-start justify-between p-[60px] relative size-full">
        <Frame272 />
        <Frame273 />
        <Frame106 />
      </div>
    </div>
  );
}

function Frame98() {
  return (
    <div className="h-[665px] relative shrink-0 w-full">
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex gap-[20px] items-center pb-[60px] px-[60px] relative size-full">
          <Frame212 />
          <div className="flex h-[33px] items-center justify-center relative shrink-0 w-[45px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
            <div className="-rotate-90 flex-none">
              <Frame249 />
            </div>
          </div>
          <Frame213 />
          <div className="flex h-[33px] items-center justify-center relative shrink-0 w-[45px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
            <div className="-rotate-90 flex-none">
              <Frame250 />
            </div>
          </div>
          <Frame214 />
        </div>
      </div>
    </div>
  );
}

function Frame145() {
  return (
    <div className="absolute content-stretch flex flex-col h-[1080px] items-center left-0 top-0">
      <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative shrink-0 w-[1920px]" data-name="Titre">
        <Frame25 />
        <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">Projection</p>
        <Frame70 />
        <Frame146 />
      </div>
      <Frame98 />
    </div>
  );
}

function PartieGauche11() {
  return (
    <div className="bg-white flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <Frame145 />
      <p className="absolute font-['Geist:Regular',sans-serif] font-normal leading-[1.5] left-[60px] text-[#8a8a8a] text-[18px] top-[1000px] w-[720px] whitespace-pre-wrap">{`Tantum autem cuique tribuendum, primum quantum ipse efficere possis,  deinde etiam quantum ille quem diligas atque adiuves, sustinere.`}</p>
    </div>
  );
}

function PitchDeck9() {
  return (
    <div className="bg-white content-stretch flex items-center overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 30">
      <PartieGauche11 />
    </div>
  );
}

function Logo16() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame26() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo16 />
    </div>
  );
}

function Frame71() {
  return (
    <div className="content-stretch flex gap-[16px] items-center justify-center relative shrink-0 w-full">
      <div className="flex h-[0.333px] items-center justify-center relative shrink-0 w-[34px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
        <div className="flex-none rotate-[-0.56deg]">
          <div className="h-0 relative w-[34.002px]">
            <div className="absolute inset-[-7.36px_-2.94%_-7.36px_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.0016 14.7279">
                <path d={svgPaths.p34bcc570} fill="var(--stroke-0, #1E1C1B)" id="Arrow 1" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">Sous titre ou phrase d’intro</p>
    </div>
  );
}

function Frame148() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1747 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="1747" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame147() {
  return (
    <div className="absolute content-stretch flex flex-col h-[1080px] items-center left-0 top-0 w-[1920px]">
      <div className="relative shrink-0 w-full" data-name="Titre">
        <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative w-full">
          <Frame26 />
          <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">Model</p>
          <Frame71 />
          <Frame148 />
        </div>
      </div>
    </div>
  );
}

function PartieGauche12() {
  return (
    <div className="bg-white flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <Frame147 />
    </div>
  );
}

function PitchDeck10() {
  return (
    <div className="bg-white content-stretch flex items-center overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 31">
      <PartieGauche12 />
    </div>
  );
}

function Logo17() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame27() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo17 />
    </div>
  );
}

function Frame149() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1747 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="1747" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame258() {
  return (
    <div className="content-stretch flex flex-col h-full items-center justify-center relative shrink-0 w-[60px]">
      <div className="h-0 relative shrink-0 w-full">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 60 1">
            <line id="Line 49" stroke="var(--stroke-0, black)" strokeDasharray="5 5" x2="60" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame184() {
  return (
    <div className="content-stretch flex items-start justify-center overflow-clip py-[16px] relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist:ExtraBold',sans-serif] font-extrabold leading-[1.4] min-h-px min-w-px relative text-[20px] text-center text-white uppercase">NOV 2026</p>
    </div>
  );
}

function Frame197() {
  return (
    <div className="bg-[#1e1c1b] relative rounded-[10px] shrink-0 w-full">
      <div className="flex flex-col justify-center size-full">
        <div className="content-stretch flex flex-col items-start justify-center px-[10px] relative w-full">
          <Frame184 />
        </div>
      </div>
    </div>
  );
}

function Frame198() {
  return (
    <div className="bg-[#f2f2f2] relative rounded-[10px] shrink-0 w-full">
      <div className="flex flex-col justify-center size-full">
        <div className="content-stretch flex flex-col items-start justify-center p-[30px] relative w-full">
          <div className="font-['Geist:Light',sans-serif] font-light leading-[0] relative shrink-0 text-[#1e1c1b] text-[0px] tracking-[-1px] w-full">
            <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.4] mb-[10px] text-[22px]">Post quorum necem nihilo lenius ferociens Gallus ut leo cadaveribus.</p>
            <p className="leading-[1.4] text-[22px]">pastus multa huius modi scrutabatur. quae singula narrare non refert, me professione modum, quod evitandum est, excedamus.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame257() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[20px] h-full items-center justify-end min-h-px min-w-px relative">
      <Frame197 />
      <Frame198 />
    </div>
  );
}

function Frame259() {
  return (
    <div className="content-stretch flex flex-col h-full items-center justify-center relative shrink-0 w-[60px]">
      <div className="h-0 relative shrink-0 w-full">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 60 1">
            <line id="Line 49" stroke="var(--stroke-0, black)" strokeDasharray="5 5" x2="60" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame199() {
  return (
    <div className="bg-[#f2f2f2] relative rounded-[10px] shrink-0 w-full">
      <div className="flex flex-col justify-center size-full">
        <div className="content-stretch flex flex-col items-start justify-center p-[30px] relative w-full">
          <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.4] relative shrink-0 text-[#1e1c1b] text-[22px] tracking-[-1px] w-full">Post quorum necem nihilo lenius ferociens Gallus ut leo cadaveribus.</p>
        </div>
      </div>
    </div>
  );
}

function Frame185() {
  return (
    <div className="content-stretch flex items-start justify-center overflow-clip py-[16px] relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist:ExtraBold',sans-serif] font-extrabold leading-[1.4] min-h-px min-w-px relative text-[20px] text-center text-white uppercase">NOV 2026</p>
    </div>
  );
}

function Frame201() {
  return (
    <div className="bg-[#1e1c1b] relative rounded-[10px] shrink-0 w-full">
      <div className="flex flex-col justify-center size-full">
        <div className="content-stretch flex flex-col items-start justify-center px-[10px] relative w-full">
          <Frame185 />
        </div>
      </div>
    </div>
  );
}

function Frame202() {
  return (
    <div className="h-[303px] relative rounded-[10px] shrink-0 w-full">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none rounded-[10px] size-full" src={imgFrame2147238773} />
      <div className="flex flex-col justify-center size-full">
        <div className="size-full" />
      </div>
    </div>
  );
}

function Frame260() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[20px] h-[361px] items-center min-h-px min-w-px relative">
      <Frame199 />
      <Frame201 />
      <Frame202 />
    </div>
  );
}

function Frame261() {
  return (
    <div className="content-stretch flex flex-col h-full items-center justify-center relative shrink-0 w-[60px]">
      <div className="h-0 relative shrink-0 w-full">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 60 1">
            <line id="Line 49" stroke="var(--stroke-0, black)" strokeDasharray="5 5" x2="60" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame203() {
  return (
    <div className="h-[303px] relative rounded-[10px] shrink-0 w-full">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none rounded-[10px] size-full" src={imgFrame2147238773} />
      <div className="flex flex-col justify-center size-full">
        <div className="size-full" />
      </div>
    </div>
  );
}

function Frame186() {
  return (
    <div className="content-stretch flex items-start justify-center overflow-clip py-[16px] relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist:ExtraBold',sans-serif] font-extrabold leading-[1.4] min-h-px min-w-px relative text-[20px] text-center text-white uppercase">NOV 2026</p>
    </div>
  );
}

function Frame204() {
  return (
    <div className="bg-[#1e1c1b] relative rounded-[10px] shrink-0 w-full">
      <div className="flex flex-col justify-center size-full">
        <div className="content-stretch flex flex-col items-start justify-center px-[10px] relative w-full">
          <Frame186 />
        </div>
      </div>
    </div>
  );
}

function Frame205() {
  return (
    <div className="bg-[#f2f2f2] relative rounded-[10px] shrink-0 w-full">
      <div className="flex flex-col justify-center size-full">
        <div className="content-stretch flex flex-col items-start justify-center p-[30px] relative w-full">
          <p className="font-['Geist:Light',sans-serif] font-light leading-[1.4] relative shrink-0 text-[#1e1c1b] text-[22px] tracking-[-1px] w-full">Astus multa huius modi scrutabatur. quae singula narrare non refert, me professione modum, quod evitandum est, excedamus.</p>
        </div>
      </div>
    </div>
  );
}

function Frame262() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[20px] h-[485px] items-center justify-end min-h-px min-w-px relative">
      <Frame203 />
      <Frame204 />
      <Frame205 />
    </div>
  );
}

function Frame263() {
  return (
    <div className="content-stretch flex flex-col h-full items-center justify-center relative shrink-0 w-[60px]">
      <div className="h-0 relative shrink-0 w-full">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 60 1">
            <line id="Line 49" stroke="var(--stroke-0, black)" strokeDasharray="5 5" x2="60" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame206() {
  return (
    <div className="bg-[#f2f2f2] relative rounded-[10px] shrink-0 w-full">
      <div className="flex flex-col justify-center size-full">
        <div className="content-stretch flex flex-col items-start justify-center p-[30px] relative w-full">
          <div className="font-['Geist:Light',sans-serif] font-light leading-[0] relative shrink-0 text-[#1e1c1b] text-[0px] tracking-[-1px] w-full">
            <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.4] mb-[10px] text-[22px]">Post quorum necem nihilo lenius ferociens Gallus ut leo cadaveribus.</p>
            <p className="leading-[1.4] text-[22px]">pastus multa huius modi scrutabatur. quae singula narrare non refert, me professione modum, quod evitandum est, excedamus.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame189() {
  return (
    <div className="content-stretch flex items-start justify-center overflow-clip py-[16px] relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist:ExtraBold',sans-serif] font-extrabold leading-[1.4] min-h-px min-w-px relative text-[20px] text-center text-white uppercase">NOV 2026</p>
    </div>
  );
}

function Frame207() {
  return (
    <div className="bg-[#1e1c1b] relative rounded-[10px] shrink-0 w-full">
      <div className="flex flex-col justify-center size-full">
        <div className="content-stretch flex flex-col items-start justify-center px-[10px] relative w-full">
          <Frame189 />
        </div>
      </div>
    </div>
  );
}

function Frame264() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[20px] h-full items-center min-h-px min-w-px relative">
      <Frame206 />
      <Frame207 />
    </div>
  );
}

function Frame265() {
  return (
    <div className="content-stretch flex flex-col h-full items-center justify-center relative shrink-0 w-[60px]">
      <div className="h-0 relative shrink-0 w-full">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 60 1">
            <line id="Line 49" stroke="var(--stroke-0, black)" strokeDasharray="5 5" x2="60" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame190() {
  return (
    <div className="content-stretch flex items-start justify-center overflow-clip py-[16px] relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist:ExtraBold',sans-serif] font-extrabold leading-[1.4] min-h-px min-w-px relative text-[20px] text-center text-white uppercase">NOV 2026</p>
    </div>
  );
}

function Frame208() {
  return (
    <div className="bg-[#1e1c1b] relative rounded-[10px] shrink-0 w-full">
      <div className="flex flex-col justify-center size-full">
        <div className="content-stretch flex flex-col items-start justify-center px-[10px] relative w-full">
          <Frame190 />
        </div>
      </div>
    </div>
  );
}

function Frame209() {
  return (
    <div className="bg-[#f2f2f2] relative rounded-[10px] shrink-0 w-full">
      <div className="flex flex-col justify-center size-full">
        <div className="content-stretch flex flex-col items-start justify-center p-[30px] relative w-full">
          <div className="font-['Geist:Light',sans-serif] font-light leading-[0] relative shrink-0 text-[#1e1c1b] text-[0px] tracking-[-1px] w-full">
            <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.4] mb-[10px] text-[22px]">Post quorum necem nihilo lenius ferociens Gallus ut leo cadaveribus.</p>
            <p className="leading-[1.4] text-[22px]">pastus multa huius modi scrutabatur. quae singula narrare non refert, me professione modum, quod evitandum est, excedamus.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame266() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[20px] h-full items-center justify-end min-h-px min-w-px relative">
      <Frame208 />
      <Frame209 />
    </div>
  );
}

function Frame267() {
  return (
    <div className="content-stretch flex flex-col h-full items-center justify-center relative shrink-0 w-[60px]">
      <div className="h-0 relative shrink-0 w-full">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 60 1">
            <line id="Line 49" stroke="var(--stroke-0, black)" strokeDasharray="5 5" x2="60" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame200() {
  return (
    <div className="absolute content-stretch flex h-[693px] items-center left-0 top-[284px] w-[1918px]">
      <Frame258 />
      <Frame257 />
      <Frame259 />
      <Frame260 />
      <Frame261 />
      <Frame262 />
      <Frame263 />
      <Frame264 />
      <Frame265 />
      <Frame266 />
      <Frame267 />
    </div>
  );
}

function PartieGauche13() {
  return (
    <div className="bg-white flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <div className="absolute content-stretch flex flex-col gap-[48px] items-start left-0 p-[60px] top-0 w-[1920px]" data-name="Titre">
        <Frame27 />
        <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">Roadmap</p>
        <Frame149 />
      </div>
      <Frame200 />
    </div>
  );
}

function PitchDeck11() {
  return (
    <div className="bg-white content-stretch flex items-center overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 33">
      <PartieGauche13 />
    </div>
  );
}

function Logo18() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g id="Calque_1" />
      </svg>
    </div>
  );
}

function Frame28() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo18 />
    </div>
  );
}

function Frame151() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 470 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="470" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame182() {
  return (
    <div className="absolute content-stretch flex flex-col items-start left-[317px] top-0 w-[643px]">
      <div className="relative shrink-0 w-full" data-name="Titre">
        <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative w-full">
          <Frame28 />
          <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">{`Founder & CEO`}</p>
          <Frame151 />
        </div>
      </div>
    </div>
  );
}

function Frame152() {
  return (
    <div className="h-[17px] relative shrink-0 w-[20px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20 17">
        <g id="Frame 1171276329">
          <line id="Line 1" stroke="var(--stroke-0, #1E1C1B)" x2="20" y1="8" y2="8" />
        </g>
      </svg>
    </div>
  );
}

function Frame44() {
  return (
    <div className="content-stretch flex gap-[16px] items-start relative shrink-0 w-full">
      <Frame152 />
      <p className="flex-[1_0_0] font-['Geist:SemiBold',sans-serif] font-semibold leading-[0] min-h-px min-w-px relative text-[#1e1c1b] text-[0px] tracking-[-1px]">
        <span className="leading-[1.5] text-[24px]">{`Suivi de l'etude du dossier MICA,`}</span>
        <span className="font-['Geist:Regular',sans-serif] font-normal leading-[1.5] text-[24px]">{` déposé à l’AMF ;`}</span>
      </p>
    </div>
  );
}

function Frame153() {
  return (
    <div className="h-[17px] relative shrink-0 w-[20px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20 17">
        <g id="Frame 1171276329">
          <line id="Line 1" stroke="var(--stroke-0, #1E1C1B)" x2="20" y1="8" y2="8" />
        </g>
      </svg>
    </div>
  );
}

function Frame45() {
  return (
    <div className="content-stretch flex gap-[16px] items-start relative shrink-0 w-full">
      <Frame153 />
      <p className="flex-[1_0_0] font-['Geist:SemiBold',sans-serif] font-semibold leading-[0] min-h-px min-w-px relative text-[#1e1c1b] text-[0px] tracking-[-1px]">
        <span className="leading-[1.5] text-[24px]">Structurer les équipes</span>
        <span className="font-['Geist:Regular',sans-serif] font-normal leading-[1.5] text-[24px]">{` commerciales et produits ;`}</span>
      </p>
    </div>
  );
}

function Frame154() {
  return (
    <div className="h-[17px] relative shrink-0 w-[20px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20 17">
        <g id="Frame 1171276329">
          <line id="Line 1" stroke="var(--stroke-0, #1E1C1B)" x2="20" y1="8" y2="8" />
        </g>
      </svg>
    </div>
  );
}

function Frame40() {
  return (
    <div className="content-stretch flex gap-[16px] items-start relative shrink-0 w-full">
      <Frame154 />
      <p className="flex-[1_0_0] font-['Geist:SemiBold',sans-serif] font-semibold leading-[0] min-h-px min-w-px relative text-[#1e1c1b] text-[0px] tracking-[-1px]">
        <span className="leading-[1.5] text-[24px]">Poursuivre le déploiement du réseau CGP</span>
        <span className="font-['Geist:Regular',sans-serif] font-normal leading-[1.5] text-[24px]">{` en France et en Europe ;`}</span>
      </p>
    </div>
  );
}

function Frame165() {
  return (
    <div className="content-stretch flex flex-col gap-[30px] items-start relative shrink-0 w-full">
      <Frame44 />
      <Frame45 />
      <Frame40 />
    </div>
  );
}

function Frame177() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[40px] items-end left-[318px] pb-[60px] pt-[40px] px-[60px] top-[704px] w-[642px]">
      <div aria-hidden="true" className="absolute border-[#4f46e5] border-solid border-t inset-0 pointer-events-none" />
      <p className="font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] relative shrink-0 text-[#4f46e5] text-[24px] uppercase w-full">Ses missions principales</p>
      <Frame165 />
    </div>
  );
}

function Frame183() {
  return (
    <div className="content-stretch flex flex-col font-['Geist:Bold',sans-serif] font-bold gap-[10px] items-start leading-[1.2] relative shrink-0 w-full">
      <p className="relative shrink-0 text-[28px] w-full">Gael Itier</p>
      <p className="relative shrink-0 text-[14px] uppercase w-full">Titre et fonction</p>
    </div>
  );
}

function Frame29() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[30px] h-[373px] items-start left-[317px] px-[60px] text-[#1e1c1b] top-[293px] w-[643px]">
      <Frame183 />
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[18px] w-full">Un produit structuré qui vise un rendement de 7% par an, une exposition à la hausse du Bitcoin et une protection de capital jusqu’à 100% de la baisse du Bitcoin</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[18px] w-full whitespace-pre-wrap">{`Batnae municipium in Anthemusia conditum Macedonum manu priscorum ab  Euphrate flumine brevi spatio disparatur, refertum mercatoribus  opulentis, ubi annua sollemnitate prope Septembris initium mensis ad  nundinas magna promiscuae fortunae convenit multitudo ad commercanda  quae Indi mittunt et Seres aliaque plurima vehi terra marique consueta.`}</p>
    </div>
  );
}

function Frame178() {
  return (
    <div className="absolute h-[1080px] right-[642px] top-0 w-[320px]">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <img alt="" className="absolute h-[113.8%] left-[-179.12%] max-w-none top-[-2.26%] w-[458.23%]" src={imgFrame2147238663} />
      </div>
    </div>
  );
}

function Frame150() {
  return (
    <div className="absolute h-[1080px] left-0 top-0 w-[960px]">
      <Frame182 />
      <Frame177 />
      <Frame29 />
      <Frame178 />
    </div>
  );
}

function PartieGauche14() {
  return (
    <div className="bg-white h-[1080px] overflow-clip relative shrink-0 w-[960px]" data-name="Partie Gauche">
      <Frame150 />
    </div>
  );
}

function Logo19() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame30() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">&nbsp;</p>
      <Logo19 />
    </div>
  );
}

function Frame158() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 787 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="787" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame179() {
  return (
    <div className="h-full relative rounded-[10px] shrink-0 w-[160px]">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none rounded-[10px] size-full" src={imgFrame2147238663} />
      <div className="flex flex-col items-center justify-end size-full">
        <div className="size-full" />
      </div>
    </div>
  );
}

function Frame192() {
  return (
    <div className="content-stretch flex flex-col font-['Geist:Bold',sans-serif] font-bold gap-[10px] items-start leading-[1.2] relative shrink-0 w-full">
      <p className="relative shrink-0 text-[24px] w-full">Prénom Nom</p>
      <p className="relative shrink-0 text-[14px] uppercase w-full">Titre et fonction</p>
    </div>
  );
}

function Frame31() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-start min-h-px min-w-px relative text-white">
      <Frame192 />
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[18px] w-full">Un produit structuré qui vise un rendement de 7% par an.</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[18px] w-full whitespace-pre-wrap">{`Batnae municipium in Anthemusia conditum Macedonum manu priscorum ab  Euphrate flumine brevi spatio disparatur.`}</p>
    </div>
  );
}

function Frame191() {
  return (
    <div className="content-stretch flex flex-[1_0_0] gap-[40px] items-center min-h-px min-w-px relative w-full">
      <Frame179 />
      <Frame31 />
    </div>
  );
}

function Frame180() {
  return (
    <div className="h-full relative rounded-[10px] shrink-0 w-[161px]">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none rounded-[10px] size-full" src={imgFrame2147238663} />
      <div className="flex flex-col items-center justify-end size-full">
        <div className="size-full" />
      </div>
    </div>
  );
}

function Frame194() {
  return (
    <div className="content-stretch flex flex-col font-['Geist:Bold',sans-serif] font-bold gap-[10px] items-start leading-[1.2] relative shrink-0 w-full">
      <p className="relative shrink-0 text-[24px] w-full">Prénom Nom</p>
      <p className="relative shrink-0 text-[14px] uppercase w-full">Titre et fonction</p>
    </div>
  );
}

function Frame32() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-start min-h-px min-w-px relative text-white">
      <Frame194 />
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[18px] w-full">Un produit structuré qui vise un rendement de 7% par an, une exposition à la hausse du Bitcoin.</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[18px] w-full whitespace-pre-wrap">{`Batnae municipium in Anthemusia conditum Macedonum manu priscorum ab  Euphrate flumine brevi spatio disparatur.`}</p>
    </div>
  );
}

function Frame193() {
  return (
    <div className="content-stretch flex flex-[1_0_0] gap-[40px] items-center min-h-px min-w-px relative w-full">
      <Frame180 />
      <Frame32 />
    </div>
  );
}

function Frame181() {
  return (
    <div className="h-full relative rounded-[10px] shrink-0 w-[161px]">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none rounded-[10px] size-full" src={imgFrame2147238663} />
      <div className="flex flex-col items-center justify-end size-full">
        <div className="size-full" />
      </div>
    </div>
  );
}

function Frame196() {
  return (
    <div className="content-stretch flex flex-col font-['Geist:Bold',sans-serif] font-bold gap-[10px] items-start leading-[1.2] relative shrink-0 w-full">
      <p className="relative shrink-0 text-[24px] w-full">Prénom Nom</p>
      <p className="relative shrink-0 text-[14px] uppercase w-full">Titre et fonction</p>
    </div>
  );
}

function Frame33() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-start min-h-px min-w-px relative text-white">
      <Frame196 />
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.5] relative shrink-0 text-[18px] w-full">Un produit structuré qui vise un rendement de 7% par an, une exposition.</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[1.5] relative shrink-0 text-[18px] w-full whitespace-pre-wrap">{`Batnae municipium in Anthemusia conditum Macedonum manu priscorum ab  Euphrate flumine brevi spatio disparatur.`}</p>
    </div>
  );
}

function Frame195() {
  return (
    <div className="content-stretch flex flex-[1_0_0] gap-[40px] items-center min-h-px min-w-px relative w-full">
      <Frame181 />
      <Frame33 />
    </div>
  );
}

function Frame286() {
  return (
    <div className="flex-[1_0_0] min-h-px min-w-px relative w-full">
      <div className="content-stretch flex flex-col gap-[40px] items-start pb-[60px] px-[60px] relative size-full">
        <Frame191 />
        <Frame193 />
        <Frame195 />
      </div>
    </div>
  );
}

function Frame157() {
  return (
    <div className="bg-[#1e1c1b] content-stretch flex flex-[1_0_0] flex-col h-[1080px] items-center min-h-px min-w-px overflow-clip relative">
      <div className="absolute flex h-[960px] items-center justify-center left-[-105px] top-[-2px] w-[1634px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "1637" } as React.CSSProperties}>
        <div className="flex-none rotate-90">
          <div className="h-[1634px] relative w-[960px]" data-name="Vector">
            <img alt="" className="absolute block max-w-none size-full" height="1634" src={imgVector} width="960" />
          </div>
        </div>
      </div>
      <div className="relative shrink-0 w-full" data-name="Titre">
        <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative w-full">
          <Frame30 />
          <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[60px] text-white w-full">Core Team</p>
          <Frame158 />
        </div>
      </div>
      <Frame286 />
    </div>
  );
}

function PitchDeck12() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex items-center overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 34">
      <PartieGauche14 />
      <Frame157 />
    </div>
  );
}

function Logo20() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame34() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo20 />
    </div>
  );
}

function Frame159() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1747 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="1747" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Calque1() {
  return (
    <div className="h-[96px] relative shrink-0 w-[206px]" data-name="Calque_1">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 206 96">
        <g clipPath="url(#clip0_1_2213)" id="Calque_1">
          <path d={svgPaths.p28b7b180} fill="var(--fill-0, white)" id="Vector" />
          <path d={svgPaths.p1c8adf80} fill="var(--fill-0, white)" id="Vector_2" />
        </g>
        <defs>
          <clipPath id="clip0_1_2213">
            <rect fill="white" height="96" width="206" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Calque2() {
  return (
    <div className="h-[102px] relative shrink-0 w-[189px]" data-name="Calque_1">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 189 102">
        <g clipPath="url(#clip0_1_1734)" id="Calque_1">
          <path clipRule="evenodd" d={svgPaths.pb626880} fill="var(--fill-0, #E30F13)" fillRule="evenodd" id="Vector" />
          <path clipRule="evenodd" d={svgPaths.p9f9f400} fill="var(--fill-0, #E30F13)" fillRule="evenodd" id="Vector_2" />
          <path clipRule="evenodd" d={svgPaths.p31261d70} fill="var(--fill-0, #E30F13)" fillRule="evenodd" id="Vector_3" />
          <path clipRule="evenodd" d={svgPaths.p33f96200} fill="var(--fill-0, #E30F13)" fillRule="evenodd" id="Vector_4" />
          <path clipRule="evenodd" d={svgPaths.pf27ca00} fill="var(--fill-0, #E30F13)" fillRule="evenodd" id="Vector_5" />
          <path clipRule="evenodd" d={svgPaths.p1a3508aa} fill="var(--fill-0, #0089C8)" fillRule="evenodd" id="Vector_6" />
          <path clipRule="evenodd" d={svgPaths.p2b742380} fill="var(--fill-0, #E30F13)" fillRule="evenodd" id="Vector_7" />
          <path clipRule="evenodd" d={svgPaths.pd238e80} fill="var(--fill-0, #0089C8)" fillRule="evenodd" id="Vector_8" />
          <path clipRule="evenodd" d={svgPaths.p13badd00} fill="var(--fill-0, #0089C8)" fillRule="evenodd" id="Vector_9" />
          <path clipRule="evenodd" d={svgPaths.pa71eb00} fill="var(--fill-0, #0089C8)" fillRule="evenodd" id="Vector_10" />
          <path clipRule="evenodd" d={svgPaths.p1755b400} fill="var(--fill-0, #0089C8)" fillRule="evenodd" id="Vector_11" />
          <path clipRule="evenodd" d={svgPaths.p127a0b00} fill="var(--fill-0, #0089C8)" fillRule="evenodd" id="Vector_12" />
        </g>
        <defs>
          <clipPath id="clip0_1_1734">
            <rect fill="white" height="102" width="189" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame216() {
  return (
    <div className="content-stretch flex gap-[12px] items-center justify-center relative shrink-0">
      <div className="h-[58px] relative shrink-0 w-[58.704px]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 58.7043 58">
          <path d={svgPaths.p2b851980} fill="var(--fill-0, white)" id="Vector" />
        </svg>
      </div>
      <p className="font-['Prompt:Medium',sans-serif] leading-[28px] not-italic relative shrink-0 text-[28px] text-white tracking-[0.42px] whitespace-pre">
        {`Cloud-native `}
        <br aria-hidden="true" />
        architecture
      </p>
    </div>
  );
}

function Calque3() {
  return (
    <div className="h-[44px] relative shrink-0 w-[293px]" data-name="Calque_1">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 293 44">
        <g clipPath="url(#clip0_1_1715)" id="Calque_1">
          <path d={svgPaths.p3225dd00} fill="var(--fill-0, white)" id="Vector" />
          <path d={svgPaths.p8337480} fill="var(--fill-0, white)" id="Vector_2" />
          <path d={svgPaths.p1f4de780} fill="var(--fill-0, white)" id="Vector_3" />
          <path d={svgPaths.p196cf900} fill="var(--fill-0, white)" id="Vector_4" />
          <path d={svgPaths.p1bb9d5f0} fill="var(--fill-0, white)" id="Vector_5" />
          <path d={svgPaths.p17f85700} fill="var(--fill-0, white)" id="Vector_6" />
          <path d={svgPaths.pe84f480} fill="var(--fill-0, white)" id="Vector_7" />
          <path d={svgPaths.p1e98d280} fill="var(--fill-0, #4695EB)" id="Vector_8" />
          <path d={svgPaths.p12602740} fill="var(--fill-0, #FF004A)" id="Vector_9" />
          <path d={svgPaths.p15106932} fill="var(--fill-0, white)" id="Vector_10" />
          <path d={svgPaths.p12923080} fill="var(--fill-0, #4695EB)" id="Vector_11" />
          <path d={svgPaths.pdfeb080} fill="var(--fill-0, #FF004A)" id="Vector_12" />
          <path d={svgPaths.pbb5c8b0} fill="var(--fill-0, white)" id="Vector_13" />
          <path d={svgPaths.p1f8d7400} fill="var(--fill-0, #4695EB)" id="Vector_14" />
          <path d={svgPaths.p39d1e00} fill="var(--fill-0, #FF004A)" id="Vector_15" />
          <path d={svgPaths.p101bcb00} fill="var(--fill-0, white)" id="Vector_16" />
          <path d={svgPaths.p19043c00} fill="var(--fill-0, #4695EB)" id="Vector_17" />
        </g>
        <defs>
          <clipPath id="clip0_1_1715">
            <rect fill="white" height="44" width="293" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Logos() {
  return (
    <div className="absolute inset-[0_-0.01%_-0.01%_0]" data-name="logos">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 60.0016 60.0014">
        <g id="logos">
          <path d={svgPaths.p36e56180} fill="var(--fill-0, #6DB33F)" id="Vector" />
        </g>
      </svg>
    </div>
  );
}

function Layer5() {
  return (
    <div className="absolute contents inset-[0_-0.01%_-0.01%_0]" data-name="Layer_2">
      <Logos />
    </div>
  );
}

function Calque4() {
  return (
    <div className="overflow-clip relative shrink-0 size-[60px]" data-name="Calque_1">
      <Layer5 />
    </div>
  );
}

function Frame217() {
  return (
    <div className="content-stretch flex gap-[12px] items-center justify-center relative shrink-0">
      <Calque4 />
      <p className="font-['Prompt:Medium',sans-serif] leading-[28px] not-italic relative shrink-0 text-[28px] text-white tracking-[0.42px] whitespace-nowrap">Spring Boot</p>
    </div>
  );
}

function Frame107() {
  return (
    <div className="bg-[rgba(255,255,255,0.04)] h-[200px] relative rounded-[10px] shrink-0 w-full">
      <div aria-hidden="true" className="absolute border border-[#707070] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex items-center justify-between p-[60px] relative size-full">
          <Calque1 />
          <Calque2 />
          <Frame216 />
          <Calque3 />
          <Frame217 />
        </div>
      </div>
    </div>
  );
}

function Frame215() {
  return (
    <div className="content-stretch flex flex-col gap-[40px] items-start relative shrink-0 w-full">
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[28px] text-white w-full">Backend</p>
      <Frame107 />
    </div>
  );
}

function Group() {
  return (
    <div className="absolute contents inset-[41.69%_73.71%_2.4%_5.28%]" data-name="Group">
      <div className="absolute inset-[41.69%_73.71%_2.4%_5.28%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-15.645px_-35.857px] mask-size-[69.492px_86px]" data-name="Rectangle" style={{ maskImage: `url('${imgRectangle}')` }}>
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <img alt="" className="absolute left-0 max-w-none size-full top-0" src={imgRectangle1} />
        </div>
      </div>
      <div className="absolute inset-[46.16%_76.52%_11.54%_6.71%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-19.859px_-39.697px] mask-size-[69.492px_86px]" data-name="Vector" style={{ maskImage: `url('${imgRectangle}')` }}>
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 49.6328 36.3831">
          <path d={svgPaths.p53ec580} fill="var(--fill-0, #54C5F8)" id="Vector" />
        </svg>
      </div>
    </div>
  );
}

function ClipPathGroup() {
  return (
    <div className="absolute contents inset-[0_76.52%_0_0]" data-name="Clip path group">
      <Group />
    </div>
  );
}

function Group1() {
  return (
    <div className="absolute inset-[0_76.52%_34.61%_0] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[0px_0px] mask-size-[69.492px_86px]" data-name="Group" style={{ maskImage: `url('${imgRectangle}')` }}>
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 69.492 56.2339">
        <g id="Group">
          <path d={svgPaths.p1dd2d980} fill="var(--fill-0, #54C5F8)" id="Vector" />
        </g>
      </svg>
    </div>
  );
}

function ClipPathGroup1() {
  return (
    <div className="absolute contents inset-[0_76.52%_0_0]" data-name="Clip path group">
      <Group1 />
    </div>
  );
}

function Group2() {
  return (
    <div className="absolute inset-[73.08%_76.52%_0_11.18%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-33.094px_-62.852px] mask-size-[69.492px_86px]" data-name="Group" style={{ maskImage: `url('${imgRectangle}')` }}>
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 36.3984 23.1492">
        <g id="Group">
          <path d={svgPaths.p30c4c880} fill="var(--fill-0, #01579B)" id="Vector" />
        </g>
      </svg>
    </div>
  );
}

function ClipPathGroup2() {
  return (
    <div className="absolute contents inset-[0_76.52%_0_0]" data-name="Clip path group">
      <Group2 />
    </div>
  );
}

function Group3() {
  return (
    <div className="absolute inset-[73.08%_82.19%_11.54%_11.18%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-33.094px_-62.852px] mask-size-[69.492px_86px]" data-name="Group" style={{ maskImage: `url('${imgRectangle}')` }}>
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 19.6314 13.2288">
        <g id="Group">
          <path d={svgPaths.p6310c40} fill="url(#paint0_linear_1_1691)" id="Vector" />
        </g>
        <defs>
          <linearGradient gradientUnits="userSpaceOnUse" id="paint0_linear_1_1691" x1="3.86024" x2="13.7148" y1="15.7835" y2="5.92479">
            <stop stopColor="#1A237E" stopOpacity="0.4" />
            <stop offset="1" stopColor="#1A237E" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

function ClipPathGroup3() {
  return (
    <div className="absolute contents inset-[0_76.52%_0_0]" data-name="Clip path group">
      <Group3 />
    </div>
  );
}

function Group4() {
  return (
    <div className="absolute inset-[57.7%_84.35%_11.54%_6.71%] mask-alpha mask-intersect mask-no-clip mask-no-repeat mask-position-[-19.852px_-49.619px] mask-size-[69.492px_86px]" data-name="Group" style={{ maskImage: `url('${imgRectangle}')` }}>
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 26.4676 26.4564">
        <g id="Group">
          <path d={svgPaths.p2edc000} fill="var(--fill-0, #29B6F6)" id="Vector" />
        </g>
      </svg>
    </div>
  );
}

function ClipPathGroup4() {
  return (
    <div className="absolute contents inset-[0_76.52%_0_0]" data-name="Clip path group">
      <Group4 />
    </div>
  );
}

function LogoVector() {
  return (
    <div className="h-[86px] overflow-clip relative shrink-0 w-[296px]" data-name="logo_vector">
      <div className="absolute inset-[21.76%_54.75%_19.84%_35.44%]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 29.0246 50.2189">
          <path d={svgPaths.p26484ff0} fill="var(--fill-0, white)" id="Vector" />
        </svg>
      </div>
      <div className="absolute inset-[21.76%_50.67%_19.88%_47.32%]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 5.9618 50.1835">
          <path d="M0 0H5.9618V50.1835H0V0Z" fill="var(--fill-0, white)" id="Vector" />
        </svg>
      </div>
      <div className="absolute inset-[38.56%_37.99%_18.55%_51.61%]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 30.7757 36.889">
          <path d={svgPaths.pe86b700} fill="var(--fill-0, white)" id="Vector" />
        </svg>
      </div>
      <div className="absolute inset-[26.82%_29.07%_18.57%_63.8%]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 21.1042 46.9631">
          <path d={svgPaths.p2d4d8800} fill="var(--fill-0, white)" id="Vector" />
        </svg>
      </div>
      <div className="absolute inset-[26.82%_20.75%_18.57%_72.13%]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 21.0991 46.9631">
          <path d={svgPaths.p29053c0} fill="var(--fill-0, white)" id="Vector" />
        </svg>
      </div>
      <div className="absolute inset-[37.25%_8.24%_18.55%_80.13%]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 34.4356 38.0138">
          <path d={svgPaths.p2b8b7a80} fill="var(--fill-0, white)" id="Vector" />
        </svg>
      </div>
      <div className="absolute inset-[37.24%_0_19.88%_93.07%]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20.5272 36.8769">
          <path d={svgPaths.p3c2ee340} fill="var(--fill-0, white)" id="Vector" />
        </svg>
      </div>
      <ClipPathGroup />
      <ClipPathGroup1 />
      <ClipPathGroup2 />
      <ClipPathGroup3 />
      <ClipPathGroup4 />
      <div className="absolute inset-[0_76.52%_0_0]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 69.492 86">
          <path d={svgPaths.p1cff3380} fill="url(#paint0_radial_1_1689)" id="Vector" />
          <defs>
            <radialGradient cx="0" cy="0" gradientTransform="translate(6.6754 8.29141) scale(105.916 105.871)" gradientUnits="userSpaceOnUse" id="paint0_radial_1_1689" r="1">
              <stop stopColor="white" stopOpacity="0.1" />
              <stop offset="1" stopColor="white" stopOpacity="0" />
            </radialGradient>
          </defs>
        </svg>
      </div>
    </div>
  );
}

function Frame219() {
  return (
    <div className="content-stretch flex gap-[12px] items-center justify-center relative shrink-0">
      <div className="h-[58px] relative shrink-0 w-[58.704px]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 58.7043 58">
          <path d={svgPaths.p2b851980} fill="var(--fill-0, white)" id="Vector" />
        </svg>
      </div>
      <p className="font-['Prompt:Medium',sans-serif] leading-[28px] not-italic relative shrink-0 text-[28px] text-white tracking-[0.42px] whitespace-nowrap">BLoC architecture</p>
    </div>
  );
}

function Calque5() {
  return (
    <div className="h-[44px] relative shrink-0 w-[219px]" data-name="Calque_1">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 219 44">
        <g clipPath="url(#clip0_1_1679)" id="Calque_1">
          <path d={svgPaths.p33bcbb00} fill="var(--fill-0, white)" id="Vector" />
          <path d={svgPaths.p149e9570} fill="var(--fill-0, white)" id="Vector_2" />
          <path d={svgPaths.p198fe310} fill="var(--fill-0, white)" id="Vector_3" />
          <path d={svgPaths.p6f56800} fill="var(--fill-0, white)" id="Vector_4" />
          <path clipRule="evenodd" d={svgPaths.pf792980} fill="var(--fill-0, white)" fillRule="evenodd" id="Vector_5" />
          <path d={svgPaths.p719dd00} fill="var(--fill-0, white)" id="Vector_6" />
          <path d={svgPaths.p2889fc80} fill="var(--fill-0, white)" id="Vector_7" />
          <path d={svgPaths.p838ce80} fill="var(--fill-0, white)" id="Vector_8" />
        </g>
        <defs>
          <clipPath id="clip0_1_1679">
            <rect fill="white" height="44" width="219" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame232() {
  return (
    <div className="content-stretch flex gap-[12px] items-center justify-center relative shrink-0">
      <div className="h-[58px] relative shrink-0 w-[58.704px]" data-name="Vector">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 58.7043 58">
          <path d={svgPaths.p2b851980} fill="var(--fill-0, white)" id="Vector" />
        </svg>
      </div>
      <p className="font-['Prompt:Medium',sans-serif] leading-[58px] not-italic relative shrink-0 text-[28px] text-white tracking-[0.42px] whitespace-nowrap">Static Site Generation (SSG)</p>
    </div>
  );
}

function Frame108() {
  return (
    <div className="bg-[rgba(255,255,255,0.04)] h-[200px] relative rounded-[10px] shrink-0 w-full">
      <div aria-hidden="true" className="absolute border border-[#707070] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex items-center justify-between p-[60px] relative size-full">
          <LogoVector />
          <Frame219 />
          <Calque5 />
          <Frame232 />
        </div>
      </div>
    </div>
  );
}

function Frame218() {
  return (
    <div className="content-stretch flex flex-col gap-[40px] items-start relative shrink-0 w-full">
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[28px] text-white w-full">Frontend</p>
      <Frame108 />
    </div>
  );
}

function Frame287() {
  return (
    <div className="relative shrink-0 w-full">
      <div className="content-stretch flex flex-col gap-[60px] items-start px-[60px] relative w-full">
        <Frame215 />
        <Frame218 />
      </div>
    </div>
  );
}

function TheMarket() {
  return (
    <div className="bg-[#1e1c1b] content-stretch flex flex-col h-[1080px] items-start overflow-clip relative shrink-0 w-[1920px]" data-name="The Market 3.1">
      <div className="absolute bottom-[-554px] flex h-[1634px] items-center justify-center left-[960px] w-[960px]">
        <div className="flex-none rotate-180">
          <div className="h-[1634px] relative w-[960px]" data-name="Vector">
            <img alt="" className="absolute block max-w-none size-full" height="1634" src={imgVector1} width="960" />
          </div>
        </div>
      </div>
      <div className="content-stretch flex flex-col gap-[48px] h-[284px] items-start p-[60px] relative shrink-0 w-[1920px]" data-name="Titre">
        <Frame34 />
        <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[60px] text-white w-full">Partenaires</p>
        <Frame159 />
      </div>
      <Frame287 />
    </div>
  );
}

function Logo21() {
  return (
    <div className="h-[25px] overflow-clip relative shrink-0 w-[188px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 188 25">
        <g clipPath="url(#clip0_1_2227)" id="Calque_1">
          <path d={svgPaths.p1d2661c0} fill="var(--fill-0, #8A8A8A)" id="Vector" />
          <g id="Group 34132">
            <path d={svgPaths.p233d7000} fill="var(--fill-0, #8A8A8A)" id="Vector_2" />
            <path d={svgPaths.p3eb2d100} fill="var(--fill-0, #8A8A8A)" id="Vector_3" />
            <path d={svgPaths.p350a400} fill="var(--fill-0, #8A8A8A)" id="Vector_4" />
            <path d={svgPaths.p15759680} fill="var(--fill-0, #8A8A8A)" id="Vector_5" />
            <path d={svgPaths.p233da780} fill="var(--fill-0, #8A8A8A)" id="Vector_6" />
            <path d={svgPaths.p19e73200} fill="var(--fill-0, #8A8A8A)" id="Vector_7" />
            <path d={svgPaths.p39c095f0} fill="var(--fill-0, #8A8A8A)" id="Vector_8" />
            <path d={svgPaths.p14f9a080} fill="var(--fill-0, #8A8A8A)" id="Vector_9" />
            <path d={svgPaths.pa33c780} fill="var(--fill-0, #8A8A8A)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2227">
            <rect fill="white" height="25" width="188" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame35() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full">
      <p className="flex-[1_0_0] font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] min-h-px min-w-px relative text-[#8a8a8a] text-[24px] uppercase">Vancelian APP</p>
      <Logo21 />
    </div>
  );
}

function Frame72() {
  return (
    <div className="content-stretch flex gap-[16px] items-center justify-center relative shrink-0 w-full">
      <div className="flex h-[0.333px] items-center justify-center relative shrink-0 w-[34px]" style={{ "--transform-inner-width": "1200", "--transform-inner-height": "19" } as React.CSSProperties}>
        <div className="flex-none rotate-[-0.56deg]">
          <div className="h-0 relative w-[34.002px]">
            <div className="absolute inset-[-7.36px_-2.94%_-7.36px_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.0016 14.7279">
                <path d={svgPaths.p34bcc570} fill="var(--stroke-0, #1E1C1B)" id="Arrow 1" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <p className="flex-[1_0_0] font-['Geist:Medium',sans-serif] font-medium leading-[1.2] min-h-px min-w-px relative text-[#1e1c1b] text-[32px]">Sous titre ou phrase d’intro</p>
    </div>
  );
}

function Frame161() {
  return (
    <div className="content-stretch flex items-start relative shrink-0 w-full">
      <div className="h-0 relative shrink-0 w-[53px]">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53 1">
            <line id="Line 1" stroke="var(--stroke-0, #4F46E5)" x2="53" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-[1_0_0] h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1747 1">
            <line id="Line 2" opacity="0.3" stroke="var(--stroke-0, #4F46E5)" x2="1747" y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Frame160() {
  return (
    <div className="absolute content-stretch flex flex-col h-[1080px] items-center left-0 top-0 w-[1920px]">
      <div className="relative shrink-0 w-full" data-name="Titre">
        <div className="content-stretch flex flex-col gap-[48px] items-start p-[60px] relative w-full">
          <Frame35 />
          <p className="font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[60px] w-full">Lorem</p>
          <Frame72 />
          <Frame161 />
        </div>
      </div>
    </div>
  );
}

function Avatar14() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[174px]" data-name="avatar">
      <div className="relative shrink-0 size-[66px]" data-name="vault">
        <div className="absolute flex inset-[6.25%_9.38%] items-center justify-center">
          <div className="-scale-y-100 flex-none h-[28px] w-[26px]">
            <div className="relative size-full" data-name="Vector">
              <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53.625 57.75">
                <path d={svgPaths.p1cd5f200} fill="var(--fill-0, #1E1C1B)" id="Vector" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame109() {
  return (
    <div className="content-stretch flex flex-col gap-[30px] items-center justify-center relative shrink-0 text-center w-full">
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[40px] w-full">Verum ad istam omnem orationem brevis est</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[1.4] relative shrink-0 text-[#8a8a8a] text-[30px] tracking-[-1px] w-full whitespace-pre-wrap">{`Erat autem diritatis eius hoc quoque indicium nec obscurum nec latens,  quod ludicris cruentis delectabatur et in circo sex vel septem  aliquotiens vetitis certaminibus.`}</p>
    </div>
  );
}

function Frame73() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-center justify-center min-h-px min-w-px relative">
      <Avatar14 />
      <Frame109 />
    </div>
  );
}

function Avatar15() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[174px]" data-name="avatar">
      <div className="relative shrink-0 size-[66px]" data-name="vault">
        <div className="absolute flex inset-[6.25%_9.38%] items-center justify-center">
          <div className="-scale-y-100 flex-none h-[28px] w-[26px]">
            <div className="relative size-full" data-name="Vector">
              <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53.625 57.75">
                <path d={svgPaths.p1cd5f200} fill="var(--fill-0, #1E1C1B)" id="Vector" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame110() {
  return (
    <div className="content-stretch flex flex-col gap-[30px] items-center justify-center relative shrink-0 text-center w-full">
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[40px] w-full">Verum ad istam omnem orationem brevis est</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[1.4] relative shrink-0 text-[#8a8a8a] text-[30px] tracking-[-1px] w-full whitespace-pre-wrap">{`Erat autem diritatis eius hoc quoque indicium nec obscurum nec latens,  quod ludicris cruentis delectabatur et in circo sex vel septem  aliquotiens vetitis certaminibus.`}</p>
    </div>
  );
}

function Frame74() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-center justify-center min-h-px min-w-px relative">
      <Avatar15 />
      <Frame110 />
    </div>
  );
}

function Avatar16() {
  return (
    <div className="bg-[#f2f2f2] content-stretch flex flex-col items-center justify-center p-[10px] relative rounded-[9999px] shrink-0 size-[174px]" data-name="avatar">
      <div className="relative shrink-0 size-[66px]" data-name="vault">
        <div className="absolute flex inset-[6.25%_9.38%] items-center justify-center">
          <div className="-scale-y-100 flex-none h-[28px] w-[26px]">
            <div className="relative size-full" data-name="Vector">
              <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 53.625 57.75">
                <path d={svgPaths.p1cd5f200} fill="var(--fill-0, #1E1C1B)" id="Vector" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Frame111() {
  return (
    <div className="content-stretch flex flex-col gap-[30px] items-center justify-center relative shrink-0 text-center w-full">
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[40px] w-full">Verum ad istam omnem orationem brevis</p>
      <p className="font-['Geist:Regular',sans-serif] font-normal leading-[1.4] relative shrink-0 text-[#8a8a8a] text-[30px] tracking-[-1px] w-full whitespace-pre-wrap">{`Erat autem diritatis eius hoc quoque indicium nec obscurum nec latens,  quod ludicris cruentis delectabatur et in circo sex vel septem  aliquotiens vetitis certaminibus.`}</p>
    </div>
  );
}

function Frame75() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col gap-[30px] items-center justify-center min-h-px min-w-px relative">
      <Avatar16 />
      <Frame111 />
    </div>
  );
}

function Frame295() {
  return (
    <div className="content-stretch flex gap-[90px] items-center px-[60px] relative shrink-0 w-[1920px]">
      <Frame73 />
      <Frame74 />
      <Frame75 />
    </div>
  );
}

function Frame291() {
  return (
    <div className="absolute content-stretch flex flex-col h-[621px] items-start justify-center left-0 pb-[120px] top-[355px]">
      <Frame295 />
    </div>
  );
}

function Frame36() {
  return (
    <div className="content-stretch flex items-center justify-center relative shrink-0 w-full">
      <p className="font-['Geist:Medium',sans-serif] font-medium leading-[1.2] relative shrink-0 text-[#1e1c1b] text-[52px] whitespace-nowrap">Conclusion: ...</p>
    </div>
  );
}

function Footer2() {
  return (
    <div className="absolute bottom-0 content-stretch flex flex-col gap-[48px] h-[171px] items-center justify-center left-0 overflow-clip p-[60px] w-[1920px]" data-name="Footer">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgPartieGauche} />
      <div className="absolute inset-[-105.85%_62.6%_-105.86%_9.63%]" data-name="Union">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 533.013 533.022">
          <path d={svgPaths.p19a3f280} fill="url(#paint0_linear_1_1999)" id="Union" />
          <defs>
            <linearGradient gradientUnits="userSpaceOnUse" id="paint0_linear_1_1999" x1="2089.39" x2="266.504" y1="-507.852" y2="533.018">
              <stop stopColor="white" />
              <stop offset="1" stopColor="#DDDDDD" />
            </linearGradient>
          </defs>
        </svg>
      </div>
      <Frame36 />
      <p className="absolute bottom-[48px] font-['Geist:Regular',sans-serif] font-normal leading-[1.4] opacity-50 right-[164px] text-[13px] text-white translate-x-full translate-y-full whitespace-nowrap">Confidential Document</p>
    </div>
  );
}

function PartieGauche15() {
  return (
    <div className="bg-white flex-[1_0_0] h-[1080px] min-h-px min-w-px overflow-clip relative" data-name="Partie Gauche">
      <Frame160 />
      <Frame291 />
      <Footer2 />
    </div>
  );
}

function PitchDeck13() {
  return (
    <div className="bg-white content-stretch flex items-center overflow-clip relative shrink-0 w-[1920px]" data-name="Pitch Deck - 36">
      <PartieGauche15 />
    </div>
  );
}

function Logo22() {
  return (
    <div className="h-[58px] overflow-clip relative shrink-0 w-[432px]" data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 432 58">
        <g clipPath="url(#clip0_1_2049)" id="Calque_1">
          <path d={svgPaths.p2b851980} fill="var(--fill-0, white)" id="Vector" />
          <g id="Group 34098">
            <path d={svgPaths.p1c1ef580} fill="var(--fill-0, white)" id="Vector_2" />
            <path d={svgPaths.p1416a000} fill="var(--fill-0, white)" id="Vector_3" />
            <path d={svgPaths.p314cc100} fill="var(--fill-0, white)" id="Vector_4" />
            <path d={svgPaths.p28d0600} fill="var(--fill-0, white)" id="Vector_5" />
            <path d={svgPaths.p1abff300} fill="var(--fill-0, white)" id="Vector_6" />
            <path d={svgPaths.p23c29040} fill="var(--fill-0, white)" id="Vector_7" />
            <path d={svgPaths.p2cf50580} fill="var(--fill-0, white)" id="Vector_8" />
            <path d={svgPaths.p1fe8f880} fill="var(--fill-0, white)" id="Vector_9" />
            <path d={svgPaths.p1e02980} fill="var(--fill-0, white)" id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_1_2049">
            <rect fill="white" height="58" width="432" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Frame296() {
  return (
    <div className="content-stretch flex flex-col font-['Geist:Light',sans-serif] font-light gap-[20px] items-start leading-[1.2] relative shrink-0 text-[20px] text-center text-white w-full">
      <p className="relative shrink-0 w-full">COLOFT - ARTEPARC - BATIMENT A SOPHIA, 965 AVENUE ROUMANILLE, 06410 BIOT, France</p>
      <p className="relative shrink-0 w-full">Adress de automata FZE</p>
      <p className="relative shrink-0 w-full">Adress de Automata Holding (Abu dhabi)</p>
    </div>
  );
}

function Frame112() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[30px] items-center left-[247px] top-[444px] w-[1426px]">
      <Logo22 />
      <Frame296 />
    </div>
  );
}

function Titre1() {
  return (
    <div className="bg-[#1e1c1b] flex-[1_0_0] min-h-px min-w-px relative w-full" data-name="Titre">
      <div className="overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex flex-col items-start justify-between p-[120px] relative size-full">
          <div className="absolute h-[1634px] left-0 top-[-560px] w-[960px]" data-name="Vector">
            <img alt="" className="absolute block max-w-none size-full" height="1634" src={imgVector2} width="960" />
          </div>
          <Frame112 />
        </div>
      </div>
    </div>
  );
}

function Frame113() {
  return (
    <div className="relative shrink-0 w-full">
      <div className="flex flex-col items-center justify-center size-full">
        <div className="content-stretch flex flex-col font-['Geist:Regular',sans-serif] font-normal gap-[60px] items-center justify-center pb-[120px] px-[60px] relative w-full">
          <p className="leading-[0] relative shrink-0 text-[0px] text-center text-white w-[1920px]">
            <span className="leading-[1.2] text-[32px]">{`Contactez Gael Itier, votre interlocuteur : par téléphone au `}</span>
            <span className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[32px]">+33 6 12 13 14 15</span>
            <span className="leading-[1.2] text-[32px]">{` ou par mail à `}</span>
            <span className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[32px]">gaelitier@vancelian.com</span>
          </p>
          <p className="leading-[1.5] min-w-full relative shrink-0 text-[#8a8a8a] text-[18px] w-[min-content]">Automata France SAS est une société française enregistrée et immatriculée sous le numéro SIREN 902 498 617. La société est enregistrée auprès de l’Autorité des Marchés Financiers (“AMF”) sous le numéro E2023-087 en tant que Prestataire de Services en Actifs Numériques (“PSAN”). Les actifs numériques sont soumis à une forte volatilité, à des risques de liquidité et de valorisation, ainsi qu’à des évolutions réglementaires et technologiques susceptibles d’affecter leur valeur. L’accès, la conservation et la cession des actifs numériques peuvent également présenter des risques opérationnels, techniques ou de contrepartie. Avant toute souscription, les investisseurs doivent s’assurer de leur compréhension des risques liés à ce type d’investissement et, le cas échéant, solliciter un conseil professionnel indépendant.</p>
        </div>
      </div>
    </div>
  );
}

function Frame162() {
  return (
    <div className="content-stretch flex flex-[1_0_0] flex-col h-[1080px] items-center justify-center min-h-px min-w-px relative">
      <Titre1 />
      <Frame113 />
    </div>
  );
}

function PitchDeck5() {
  return (
    <div className="bg-[#1e1c1b] content-stretch flex h-[1080px] items-start overflow-clip relative shrink-0 w-full" data-name="Pitch Deck - 23">
      <Frame162 />
      <p className="absolute bottom-[25px] font-['Geist:Regular',sans-serif] font-normal leading-[1.4] left-[60px] text-[#8a8a8a] text-[13px] translate-y-full whitespace-nowrap">Confidential Document</p>
    </div>
  );
}

export default function Frame() {
  return (
    <div className="content-stretch flex flex-col gap-[60px] items-end relative size-full" data-name="Frame">
      <PitchDeck />
      <PitchDeck1 />
      <PitchDeck2 />
      <PitchDeck3 />
      <PitchDeck4 />
      <PitchDeck7 />
      <PitchDeck6 />
      <PitchDeck14 />
      <PitchDeck15 />
      <PitchDeck8 />
      <CreatableInvestmentPitchTemplate />
      <CreatableInvestmentPitchTemplate2 />
      <CreatableInvestmentPitchTemplate1 />
      <CreatableInvestmentPitchTemplate3 />
      <CreatableInvestmentPitchTemplate4 />
      <PitchDeck9 />
      <PitchDeck10 />
      <PitchDeck11 />
      <PitchDeck12 />
      <TheMarket />
      <PitchDeck13 />
      <PitchDeck5 />
    </div>
  );
}