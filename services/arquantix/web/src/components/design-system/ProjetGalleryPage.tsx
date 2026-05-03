import { SectionTitle } from "@/components/design-system/extracted";
import svgPaths from "./imports/PageDeToutLesProjets/svg-a44vadv40c";
import imgImage from "./imports/PageDeToutLesProjets/0ea7b87e0fb028430d5be3bd5c0071081824fa77.png";
import imgImage1 from "./imports/PageDeToutLesProjets/b775f6f8ce6fc689a865af4fdc980d94feb91d0c.png";
import imgImage2 from "./imports/PageDeToutLesProjets/bde784c891e469bd7acf051d0c0d4e4be2f25ed4.png";
import imgImage3 from "./imports/PageDeToutLesProjets/5f529eb7a115a2504e05f35c5f648d8be648e2d5.png";
import imgSectionTextImgBackground from "./imports/PageDeToutLesProjets/ff2a47f0ecb3dba525997b8cb8f5548d1b5907de.png";

function Frame10() {
  return (
    <div className="content-stretch flex flex-col gap-[30px] items-center not-italic relative shrink-0 text-[#272727] text-center w-[1152px]">
      <div className="flex flex-col font-['Avenir:Heavy',sans-serif] justify-center leading-[0] min-w-full relative shrink-0 text-[56px] tracking-[-1.12px] w-[min-content]">
        <h1 className="block leading-none">Projects</h1>
      </div>
      <h1 className="block font-['Avenir:Roman',sans-serif] leading-[1.6] relative shrink-0 text-[18px] w-[746px]">Arquantix provides access to fractional ownership of premium real estate assets. Every investment is structured with the same discipline, transparency and governance standards expected from an institutional financial operator.</h1>
    </div>
  );
}

function Frame2() {
  return (
    <div className="bg-[#272727] content-stretch flex items-center justify-center px-[12px] py-[8px] relative rounded-[10px] shrink-0">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[normal] not-italic relative shrink-0 text-[16px] text-white whitespace-nowrap">All</p>
    </div>
  );
}

function Frame4() {
  return (
    <div className="content-stretch flex items-center justify-center px-[12px] py-[8px] relative rounded-[11px] shrink-0">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[normal] not-italic relative shrink-0 text-[#9b948d] text-[16px] whitespace-nowrap">In Progress</p>
    </div>
  );
}

function Frame3() {
  return (
    <div className="content-stretch flex items-center justify-center px-[12px] py-[8px] relative rounded-[11px] shrink-0">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[normal] not-italic relative shrink-0 text-[#9b948d] text-[16px] whitespace-nowrap">Upcoming</p>
    </div>
  );
}

function Frame5() {
  return (
    <div className="content-stretch flex items-center justify-center px-[12px] py-[8px] relative rounded-[11px] shrink-0">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[normal] not-italic relative shrink-0 text-[#9b948d] text-[16px] whitespace-nowrap">Delivered</p>
    </div>
  );
}

function Frame6() {
  return (
    <div className="bg-white content-stretch flex gap-[13px] items-center relative rounded-[16px] shrink-0">
      <div aria-hidden="true" className="absolute border border-[#e5e5e5] border-solid inset-0 pointer-events-none rounded-[16px]" />
      <Frame2 />
      <Frame4 />
      <Frame3 />
      <Frame5 />
    </div>
  );
}

function Tag() {
  return (
    <div className="bg-black content-stretch flex items-center justify-center px-[6px] py-[8px] relative rounded-[8px] shrink-0 w-[96px]" data-name="Tag 3">
      <p className="font-['Avenir:Black',sans-serif] leading-[normal] not-italic relative shrink-0 text-[10px] text-white uppercase whitespace-nowrap">Label</p>
    </div>
  );
}

function Tag2() {
  return (
    <div className="bg-black content-stretch flex items-center justify-center px-[6px] py-[8px] relative rounded-[8px] shrink-0 w-[96px]" data-name="Tag 5">
      <p className="font-['Avenir:Black',sans-serif] leading-[normal] not-italic relative shrink-0 text-[10px] text-white uppercase whitespace-nowrap">Label</p>
    </div>
  );
}

function Image() {
  return (
    <div className="h-[220px] relative shrink-0 w-full" data-name="Image">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgImage.src} />
      <div className="content-stretch flex gap-[8px] items-start p-[20px] relative size-full">
        <Tag />
        <Tag2 />
      </div>
    </div>
  );
}

function Label() {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0" data-name="Label 1">
      <div aria-hidden="true" className="absolute border-[#62656e] border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[#62656e] text-[14px] uppercase whitespace-nowrap">Japan</p>
    </div>
  );
}

function Label1() {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0" data-name="Label 3">
      <div aria-hidden="true" className="absolute border-[#62656e] border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[#62656e] text-[14px] uppercase whitespace-nowrap">2 Suites</p>
    </div>
  );
}

function Frame11() {
  return (
    <div className="content-stretch flex gap-[4px] items-center relative shrink-0">
      <Label />
      <Label1 />
    </div>
  );
}

function Label2() {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0" data-name="Label 2">
      <div aria-hidden="true" className="absolute border-black border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[14px] text-black uppercase whitespace-nowrap">€560K</p>
    </div>
  );
}

function Labels() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full" data-name="Labels">
      <Frame11 />
      <Label2 />
    </div>
  );
}

function Title() {
  return (
    <div className="content-stretch flex flex-col gap-[11px] items-start relative shrink-0 w-full" data-name="Title">
      <Labels />
      <div className="flex flex-col font-['Avenir:Heavy',sans-serif] justify-center leading-[0] not-italic relative shrink-0 text-[32px] text-black tracking-[-0.32px] whitespace-nowrap">
        <p className="leading-[1.1]">The Heights Munduk</p>
      </div>
    </div>
  );
}

function Description() {
  return (
    <div className="relative shrink-0 w-full" data-name="Description">
      <div className="flex flex-col items-center size-full">
        <div className="content-stretch flex flex-col gap-[24px] items-center p-[40px] relative w-full">
          <Title />
          <p className="font-['Avenir:Book',sans-serif] leading-[1.6] not-italic relative shrink-0 text-[#62656e] text-[14px] w-full">Exclusive mountain resort development offering premium suites with breathtaking views.</p>
        </div>
      </div>
    </div>
  );
}

function Line() {
  return (
    <div className="bg-[#62656e] h-[1px] relative shrink-0 w-full" data-name="Line" />
  );
}

function TextFrame() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[1.1] not-italic relative shrink-0 text-[12px] text-black uppercase whitespace-nowrap">15.5%</p>
      <p className="font-['Avenir:Roman',sans-serif] leading-[1.4] not-italic relative shrink-0 text-[10px] text-[#62656e] uppercase whitespace-nowrap">YIELD</p>
    </div>
  );
}

function TextFrame1() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[1.1] not-italic relative shrink-0 text-[12px] text-black uppercase whitespace-nowrap">€10K</p>
      <p className="font-['Avenir:Roman',sans-serif] leading-[1.4] not-italic relative shrink-0 text-[10px] text-[#62656e] uppercase whitespace-nowrap">MINIMUM INVESTMENT</p>
    </div>
  );
}

function Stats() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full" data-name="Stats">
      <TextFrame />
      <TextFrame1 />
    </div>
  );
}

function State() {
  return (
    <div className="relative shrink-0 w-full" data-name="State">
      <div className="flex flex-col items-center size-full">
        <div className="content-stretch flex flex-col gap-[24px] items-center px-[40px] py-[32px] relative w-full">
          <Line />
          <Stats />
        </div>
      </div>
    </div>
  );
}

function Card() {
  return (
    <div className="bg-[#f3f3f3] content-stretch flex flex-col items-start overflow-clip relative rounded-[10px] shrink-0 w-[378px]" data-name="Card 1">
      <Image />
      <Description />
      <State />
    </div>
  );
}

function Tag3() {
  return (
    <div className="bg-black content-stretch flex items-center justify-center px-[6px] py-[8px] relative rounded-[8px] shrink-0 w-[96px]" data-name="Tag 5">
      <p className="font-['Avenir:Black',sans-serif] leading-[normal] not-italic relative shrink-0 text-[10px] text-white uppercase whitespace-nowrap">Label</p>
    </div>
  );
}

function Image1() {
  return (
    <div className="h-[220px] relative shrink-0 w-full" data-name="Image">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgImage1.src} />
      <div className="content-stretch flex items-start p-[20px] relative size-full">
        <Tag3 />
      </div>
    </div>
  );
}

function Label3() {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0" data-name="Label 1">
      <div aria-hidden="true" className="absolute border-[#62656e] border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[#62656e] text-[14px] uppercase whitespace-nowrap">UAE</p>
    </div>
  );
}

function Label4() {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0" data-name="Label 3">
      <div aria-hidden="true" className="absolute border-[#62656e] border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[#62656e] text-[14px] uppercase whitespace-nowrap">1 Villa</p>
    </div>
  );
}

function Frame14() {
  return (
    <div className="content-stretch flex gap-[4px] items-center relative shrink-0">
      <Label3 />
      <Label4 />
    </div>
  );
}

function Label5() {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0" data-name="Label 2">
      <div aria-hidden="true" className="absolute border-black border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[14px] text-black uppercase whitespace-nowrap">€11.5M</p>
    </div>
  );
}

function Labels1() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full" data-name="Labels">
      <Frame14 />
      <Label5 />
    </div>
  );
}

function Title1() {
  return (
    <div className="content-stretch flex flex-col gap-[11px] items-start relative shrink-0 w-full" data-name="Title">
      <Labels1 />
      <div className="flex flex-col font-['Avenir:Heavy',sans-serif] justify-center leading-[0] not-italic relative shrink-0 text-[32px] text-black tracking-[-0.32px] whitespace-nowrap">
        <p className="leading-[1.1]">Dubai Al Barari</p>
      </div>
    </div>
  );
}

function Description1() {
  return (
    <div className="relative shrink-0 w-full" data-name="Description">
      <div className="flex flex-col items-center size-full">
        <div className="content-stretch flex flex-col gap-[24px] items-center p-[40px] relative w-full">
          <Title1 />
          <p className="font-['Avenir:Book',sans-serif] leading-[1.6] not-italic relative shrink-0 text-[#62656e] text-[14px] w-full">{`Complete renovation of a luxury villa in Al Barari, Dubai's most exclusive green community.`}</p>
        </div>
      </div>
    </div>
  );
}

function Line1() {
  return (
    <div className="bg-[#62656e] h-[1px] relative shrink-0 w-full" data-name="Line" />
  );
}

function TextFrame2() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[1.1] not-italic relative shrink-0 text-[12px] text-black uppercase whitespace-nowrap">12.8%</p>
      <p className="font-['Avenir:Roman',sans-serif] leading-[1.4] not-italic relative shrink-0 text-[10px] text-[#62656e] uppercase whitespace-nowrap">YIELD</p>
    </div>
  );
}

function TextFrame3() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[1.1] not-italic relative shrink-0 text-[12px] text-black uppercase whitespace-nowrap">€50K</p>
      <p className="font-['Avenir:Roman',sans-serif] leading-[1.4] not-italic relative shrink-0 text-[10px] text-[#62656e] uppercase whitespace-nowrap">MINIMUM INVESTMENT</p>
    </div>
  );
}

function Stats1() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full" data-name="Stats">
      <TextFrame2 />
      <TextFrame3 />
    </div>
  );
}

function State1() {
  return (
    <div className="relative shrink-0 w-full" data-name="State">
      <div className="flex flex-col items-center size-full">
        <div className="content-stretch flex flex-col gap-[24px] items-center px-[40px] py-[32px] relative w-full">
          <Line1 />
          <Stats1 />
        </div>
      </div>
    </div>
  );
}

function Card5() {
  return (
    <div className="bg-[#f3f3f3] content-stretch flex flex-col items-start overflow-clip relative rounded-[10px] shrink-0 w-[378px]" data-name="Card 2">
      <Image1 />
      <Description1 />
      <State1 />
    </div>
  );
}

function Tag4() {
  return (
    <div className="bg-black content-stretch flex items-center justify-center px-[6px] py-[8px] relative rounded-[8px] shrink-0 w-[96px]" data-name="Tag 5">
      <p className="font-['Avenir:Black',sans-serif] leading-[normal] not-italic relative shrink-0 text-[10px] text-white uppercase whitespace-nowrap">Label</p>
    </div>
  );
}

function Image2() {
  return (
    <div className="h-[220px] relative shrink-0 w-full" data-name="Image">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgImage2.src} />
      <div className="content-stretch flex items-start p-[20px] relative size-full">
        <Tag4 />
      </div>
    </div>
  );
}

function Label6() {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0" data-name="Label 1">
      <div aria-hidden="true" className="absolute border-[#62656e] border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[#62656e] text-[14px] uppercase whitespace-nowrap">Portugal</p>
    </div>
  );
}

function Label7() {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0" data-name="Label 3">
      <div aria-hidden="true" className="absolute border-[#62656e] border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[#62656e] text-[14px] uppercase whitespace-nowrap">8 Apartments</p>
    </div>
  );
}

function Frame141() {
  return (
    <div className="content-stretch flex gap-[4px] items-center relative shrink-0">
      <Label6 />
      <Label7 />
    </div>
  );
}

function Label8() {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0" data-name="Label 2">
      <div aria-hidden="true" className="absolute border-black border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[14px] text-black uppercase whitespace-nowrap">€3.2M</p>
    </div>
  );
}

function Labels2() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full" data-name="Labels">
      <Frame141 />
      <Label8 />
    </div>
  );
}

function Title2() {
  return (
    <div className="content-stretch flex flex-col gap-[11px] items-start relative shrink-0 w-full" data-name="Title">
      <Labels2 />
      <div className="flex flex-col font-['Avenir:Heavy',sans-serif] justify-center leading-[0] not-italic relative shrink-0 text-[32px] text-black tracking-[-0.32px] whitespace-nowrap">
        <p className="leading-[1.1]">Lisbon Residence</p>
      </div>
    </div>
  );
}

function Description2() {
  return (
    <div className="relative shrink-0 w-full" data-name="Description">
      <div className="flex flex-col items-center size-full">
        <div className="content-stretch flex flex-col gap-[24px] items-center p-[40px] relative w-full">
          <Title2 />
          <p className="font-['Avenir:Book',sans-serif] leading-[1.6] not-italic relative shrink-0 text-[#62656e] text-[14px] w-full">Historic building renovation in Lisbon&apos;s prime location with modern luxury apartments.</p>
        </div>
      </div>
    </div>
  );
}

function Line2() {
  return (
    <div className="bg-[#62656e] h-[1px] relative shrink-0 w-full" data-name="Line" />
  );
}

function TextFrame4() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[1.1] not-italic relative shrink-0 text-[12px] text-black uppercase whitespace-nowrap">14.2%</p>
      <p className="font-['Avenir:Roman',sans-serif] leading-[1.4] not-italic relative shrink-0 text-[10px] text-[#62656e] uppercase whitespace-nowrap">YIELD</p>
    </div>
  );
}

function TextFrame5() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[1.1] not-italic relative shrink-0 text-[12px] text-black uppercase whitespace-nowrap">€20K</p>
      <p className="font-['Avenir:Roman',sans-serif] leading-[1.4] not-italic relative shrink-0 text-[10px] text-[#62656e] uppercase whitespace-nowrap">MINIMUM INVESTMENT</p>
    </div>
  );
}

function Stats2() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full" data-name="Stats">
      <TextFrame4 />
      <TextFrame5 />
    </div>
  );
}

function State2() {
  return (
    <div className="relative shrink-0 w-full" data-name="State">
      <div className="flex flex-col items-center size-full">
        <div className="content-stretch flex flex-col gap-[24px] items-center px-[40px] py-[32px] relative w-full">
          <Line2 />
          <Stats2 />
        </div>
      </div>
    </div>
  );
}

function Card4() {
  return (
    <div className="bg-[#f3f3f3] content-stretch flex flex-col items-start overflow-clip relative rounded-[10px] shrink-0 w-[378px]" data-name="Card 3">
      <Image2 />
      <Description2 />
      <State2 />
    </div>
  );
}

function Cards() {
  return (
    <div className="content-stretch flex gap-[8px] items-start relative shrink-0 w-full" data-name="Cards">
      <Card />
      <Card5 />
      <Card4 />
    </div>
  );
}

function Tag1() {
  return (
    <div className="bg-black content-stretch flex items-center justify-center px-[6px] py-[8px] relative rounded-[8px] shrink-0 w-[96px]" data-name="Tag 3">
      <p className="font-['Avenir:Black',sans-serif] leading-[normal] not-italic relative shrink-0 text-[10px] text-white uppercase whitespace-nowrap">Label</p>
    </div>
  );
}

function Tag5() {
  return (
    <div className="bg-black content-stretch flex items-center justify-center px-[6px] py-[8px] relative rounded-[8px] shrink-0 w-[96px]" data-name="Tag 5">
      <p className="font-['Avenir:Black',sans-serif] leading-[normal] not-italic relative shrink-0 text-[10px] text-white uppercase whitespace-nowrap">Label</p>
    </div>
  );
}

function Image3() {
  return (
    <div className="h-[220px] relative shrink-0 w-full" data-name="Image">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={imgImage3.src} />
      <div className="content-stretch flex gap-[8px] items-start p-[20px] relative size-full">
        <Tag1 />
        <Tag5 />
      </div>
    </div>
  );
}

function Label9() {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0" data-name="Label 1">
      <div aria-hidden="true" className="absolute border-[#62656e] border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[#62656e] text-[14px] uppercase whitespace-nowrap">Spain</p>
    </div>
  );
}

function Label10() {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0" data-name="Label 3">
      <div aria-hidden="true" className="absolute border-[#62656e] border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[#62656e] text-[14px] uppercase whitespace-nowrap">1 Hotel</p>
    </div>
  );
}

function Frame142() {
  return (
    <div className="content-stretch flex gap-[4px] items-center relative shrink-0">
      <Label9 />
      <Label10 />
    </div>
  );
}

function Label11() {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0" data-name="Label 2">
      <div aria-hidden="true" className="absolute border-black border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[14px] text-black uppercase whitespace-nowrap">€8.5M</p>
    </div>
  );
}

function Labels3() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full" data-name="Labels">
      <Frame142 />
      <Label11 />
    </div>
  );
}

function Title3() {
  return (
    <div className="content-stretch flex flex-col gap-[11px] items-start relative shrink-0 w-full" data-name="Title">
      <Labels3 />
      <div className="flex flex-col font-['Avenir:Heavy',sans-serif] justify-center leading-[0] not-italic relative shrink-0 text-[32px] text-black tracking-[-0.32px] whitespace-nowrap">
        <p className="leading-[1.1]">Barcelona Boutique</p>
      </div>
    </div>
  );
}

function Description3() {
  return (
    <div className="relative shrink-0 w-full" data-name="Description">
      <div className="flex flex-col items-center size-full">
        <div className="content-stretch flex flex-col gap-[24px] items-center p-[40px] relative w-full">
          <Title3 />
          <p className="font-['Avenir:Book',sans-serif] leading-[1.6] not-italic relative shrink-0 text-[#62656e] text-[14px] w-full">Boutique hotel conversion in Barcelona&apos;s Gothic Quarter with premium amenities.</p>
        </div>
      </div>
    </div>
  );
}

function Line3() {
  return (
    <div className="bg-[#62656e] h-[1px] relative shrink-0 w-full" data-name="Line" />
  );
}

function TextFrame6() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[1.1] not-italic relative shrink-0 text-[12px] text-black uppercase whitespace-nowrap">13.5%</p>
      <p className="font-['Avenir:Roman',sans-serif] leading-[1.4] not-italic relative shrink-0 text-[10px] text-[#62656e] uppercase whitespace-nowrap">YIELD</p>
    </div>
  );
}

function TextFrame7() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[1.1] not-italic relative shrink-0 text-[12px] text-black uppercase whitespace-nowrap">€30K</p>
      <p className="font-['Avenir:Roman',sans-serif] leading-[1.4] not-italic relative shrink-0 text-[10px] text-[#62656e] uppercase whitespace-nowrap">MINIMUM INVESTMENT</p>
    </div>
  );
}

function Stats3() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full" data-name="Stats">
      <TextFrame6 />
      <TextFrame7 />
    </div>
  );
}

function State3() {
  return (
    <div className="relative shrink-0 w-full" data-name="State">
      <div className="flex flex-col items-center size-full">
        <div className="content-stretch flex flex-col gap-[24px] items-center px-[40px] py-[32px] relative w-full">
          <Line3 />
          <Stats3 />
        </div>
      </div>
    </div>
  );
}

function Card1() {
  return (
    <div className="bg-[#f3f3f3] content-stretch flex flex-col items-start overflow-clip relative rounded-[10px] shrink-0 w-[378px]" data-name="Card 4">
      <Image3 />
      <Description3 />
      <State3 />
    </div>
  );
}

function Cards1() {
  return (
    <div className="content-stretch flex gap-[8px] items-start relative shrink-0 w-full" data-name="Cards">
      <Card1 />
    </div>
  );
}

function Offers() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] items-center relative shrink-0 w-full" data-name="Offers">
      <Cards />
      <Cards1 />
    </div>
  );
}

function Hero() {
  return (
    <div className="content-stretch flex flex-col gap-[64px] items-center px-[64px] py-[128px] relative shrink-0 w-[1280px]" data-name="Hero">
      <Frame10 />
      <Frame6 />
      <Offers />
    </div>
  );
}

function Text() {
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-center not-italic relative shrink-0 text-center w-full" data-name="Text">
      <SectionTitle as="h1" align="center" color="#ffffff" size="module" className="whitespace-pre-wrap">
        {`Access fractional real estate `}
        <br aria-hidden="true" />
        with institutional confidence.
      </SectionTitle>
      <h1 className="block font-['Avenir:Roman',sans-serif] leading-[1.6] relative shrink-0 text-[#f3f3f3] text-[18px] w-[558px]">Access fractional real estate with institutional confidence.</h1>
    </div>
  );
}

function SubscribeButton() {
  return (
    <div className="bg-white content-stretch flex h-[36px] items-center justify-center px-[16px] py-[10px] relative rounded-[999px] shrink-0" data-name="Subscribe Button">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[1.1] not-italic relative shrink-0 text-[12px] text-black tracking-[0.06px] uppercase whitespace-nowrap">Enter the investment platform</p>
    </div>
  );
}

function Cta11() {
  return (
    <div className="content-stretch flex h-[36px] items-center relative shrink-0" data-name="CTA">
      <SubscribeButton />
    </div>
  );
}

function SectionTextImgBackground() {
  return (
    <div className="h-[454px] relative shrink-0 w-full" data-name="Section text img background">
      <div aria-hidden="true" className="absolute inset-0 pointer-events-none">
        <img alt="" className="absolute max-w-none object-cover size-full" src={imgSectionTextImgBackground.src} />
        <div className="absolute bg-[rgba(0,0,0,0.8)] inset-0" />
      </div>
      <div className="flex flex-col items-center justify-center overflow-clip rounded-[inherit] size-full">
        <div className="content-stretch flex flex-col gap-[30px] items-center justify-center p-[64px] relative size-full">
          <Text />
          <Cta11 />
        </div>
      </div>
    </div>
  );
}

function Union() {
  return (
    <div className="h-[44px] relative shrink-0 w-[203px]" data-name="Union">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 203 43.9287">
        <path d={svgPaths.p3e564200} fill="white" id="Union" />
      </svg>
    </div>
  );
}

function Instagram() {
  return (
    <div className="h-[24px] relative shrink-0 w-[24px]" data-name="Instagram">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 24 24">
        <path d={svgPaths.p14421100} fill="white" id="Instagram" />
      </svg>
    </div>
  );
}

function X() {
  return (
    <div className="h-[12px] relative shrink-0 w-[12px]" data-name="X">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <path d={svgPaths.p2c2c7000} fill="white" id="X" />
      </svg>
    </div>
  );
}

function Youtube() {
  return (
    <div className="h-[24px] relative shrink-0 w-[24px]" data-name="Youtube">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 24 24">
        <path d={svgPaths.p843b400} fill="white" id="Youtube" />
      </svg>
    </div>
  );
}

function Facebook() {
  return (
    <div className="h-[24px] relative shrink-0 w-[24px]" data-name="Facebook">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 24 24">
        <path d={svgPaths.p8dd7c00} fill="white" id="Facebook" />
      </svg>
    </div>
  );
}

function Socials() {
  return (
    <div className="content-stretch flex gap-[12px] items-center relative shrink-0" data-name="Socials">
      <Instagram />
      <X />
      <Youtube />
      <Facebook />
    </div>
  );
}

function RightArrow() {
  return (
    <div className="h-[36px] relative shrink-0 w-[36px]" data-name="Right arrow">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 36 36">
        <path d={svgPaths.p38cf7240} stroke="white" strokeLinecap="round" strokeLinejoin="round" id="Right arrow" />
      </svg>
    </div>
  );
}

function EmailField() {
  return (
    <div className="content-stretch flex items-center justify-between px-[20px] py-[12px] relative shrink-0 w-[348px]" data-name="Email field">
      <div aria-hidden="true" className="absolute border border-solid border-white inset-0 pointer-events-none rounded-[99px]" />
      <p className="font-['Avenir:Book',sans-serif] leading-[normal] not-italic relative shrink-0 text-[16px] text-white whitespace-nowrap">Enter your email</p>
      <RightArrow />
    </div>
  );
}

function NewsletterTextHeading() {
  return (
    <div className="content-stretch flex flex-col gap-[16px] items-start relative shrink-0 w-full" data-name="Newsletter text + heading">
      <h1 className="block font-['Avenir:Heavy',sans-serif] leading-[1.1] not-italic relative shrink-0 text-[24px] text-white tracking-[-0.24px] w-full">Subscribe to our newsletter</h1>
      <p className="font-['Avenir:Roman',sans-serif] leading-[1.4] not-italic relative shrink-0 text-[14px] text-white w-full">Stay updated with our latest projects and investment opportunities.</p>
    </div>
  );
}

function Newsletter() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full" data-name="Newsletter">
      <NewsletterTextHeading />
      <EmailField />
    </div>
  );
}

function Line4() {
  return (
    <div className="bg-white h-[1px] relative shrink-0 w-full" data-name="Line" />
  );
}

function Text1() {
  return (
    <div className="content-stretch flex flex-col items-start not-italic relative shrink-0 text-white w-full" data-name="Text">
      <h1 className="block font-['Avenir:Heavy',sans-serif] leading-[1.1] relative shrink-0 text-[16px] w-full">Arquantix</h1>
      <p className="font-['Avenir:Book',sans-serif] leading-[1.6] relative shrink-0 text-[14px] w-full">Professional fractional real estate investment platform.</p>
    </div>
  );
}

function Copyright() {
  return (
    <div className="content-stretch flex items-center justify-between relative shrink-0 w-full" data-name="Copyright">
      <Text1 />
      <Socials />
    </div>
  );
}

function Footer1() {
  return (
    <div className="bg-black relative shrink-0 w-full" data-name="Footer">
      <div className="flex flex-col items-center size-full">
        <div className="content-stretch flex flex-col gap-[40px] items-center p-[64px] relative w-full">
          <Union />
          <Newsletter />
          <Line4 />
          <Copyright />
        </div>
      </div>
    </div>
  );
}

function Footer() {
  return (
    <div className="content-stretch flex flex-col items-start relative shrink-0 w-[1280px]" data-name="Footer">
      <SectionTextImgBackground />
      <Footer1 />
    </div>
  );
}

function Logo() {
  return (
    <div className="h-full relative shrink-0 w-[266px]" data-name="Logo">
      <div className="flex flex-col justify-center size-full">
        <div className="content-stretch flex flex-col items-start justify-center pr-[30px] py-[30px] relative size-full">
          <div className="h-[25.771px] relative shrink-0 w-[118px]" data-name="Union">
            <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 118 25.7715">
              <path d={svgPaths.p2ef3300} fill="var(--fill-0, black)" id="Union" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

function Link1() {
  return (
    <div className="content-stretch flex items-center justify-center px-[12px] py-[8px] relative rounded-[11px] shrink-0" data-name="Link 2">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[normal] not-italic relative shrink-0 text-[#62656e] text-[16px] whitespace-nowrap">Home</p>
    </div>
  );
}

function Link() {
  return (
    <div className="bg-black content-stretch flex items-center justify-center px-[12px] py-[8px] relative rounded-[10px] shrink-0" data-name="Link 1">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[normal] not-italic relative shrink-0 text-[16px] text-white whitespace-nowrap">Projects</p>
    </div>
  );
}

function Link2() {
  return (
    <div className="content-stretch flex items-center justify-center px-[12px] py-[8px] relative rounded-[11px] shrink-0" data-name="Link 3">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[normal] not-italic relative shrink-0 text-[#62656e] text-[16px] whitespace-nowrap">About</p>
    </div>
  );
}

function Link3() {
  return (
    <div className="content-stretch flex items-center justify-center px-[12px] py-[8px] relative rounded-[11px] shrink-0" data-name="Link 4">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[normal] not-italic relative shrink-0 text-[#62656e] text-[16px] whitespace-nowrap">Help</p>
    </div>
  );
}

function Links1() {
  return (
    <div className="bg-white content-stretch flex gap-[13px] items-center relative rounded-[16px] shrink-0" data-name="Links">
      <Link1 />
      <Link />
      <Link2 />
      <Link3 />
    </div>
  );
}

function Button() {
  return (
    <a className="content-stretch cursor-pointer flex h-[36px] items-center justify-center px-[20px] py-[10px] relative rounded-[20px] shrink-0" data-name="Button" href="https://wa.me/6281353009603?text=Hello,%20I'm%20interested%20in%20The%20Heights%20Munduk" target="_blank">
      <div aria-hidden="true" className="absolute border border-[#62656e] border-solid inset-0 pointer-events-none rounded-[20px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-[1.1] not-italic relative shrink-0 text-[#62656e] text-[12px] text-center tracking-[0.06px] uppercase w-[89px]">login</p>
    </a>
  );
}

function Frame7() {
  return (
    <div className="content-stretch flex items-center relative shrink-0 w-[130px]">
      <Button />
    </div>
  );
}

function Button1() {
  return (
    <a className="bg-black content-stretch cursor-pointer flex h-[36px] items-center justify-center px-[24px] py-[11px] relative rounded-[40px] shrink-0 w-[130px]" data-name="Button" href="https://wa.me/6281353009603?text=Hello,%20I'm%20interested%20in%20The%20Heights%20Munduk" target="_blank">
      <p className="font-['Avenir:Heavy',sans-serif] leading-[1.1] not-italic relative shrink-0 text-[12px] text-center text-white tracking-[0.06px] uppercase w-[89px]">Join us</p>
    </a>
  );
}

function CallToActions() {
  return (
    <div className="content-stretch flex gap-[8px] items-center relative shrink-0" data-name="Call to actions">
      <Frame7 />
      <Button1 />
    </div>
  );
}

function Menu() {
  return (
    <div className="absolute backdrop-blur-[35px] content-stretch flex h-[64px] items-center justify-between left-0 px-[64px] rounded-[40px] top-0 w-[1280px]" data-name="Menu">
      <Logo />
      <Links1 />
      <CallToActions />
    </div>
  );
}

export default function ProjetGalleryPage() {
  return (
    <section className="bg-white content-stretch flex flex-col items-center relative size-full" data-name="Page de tout les projets">
      <Hero />
      <Menu />
    </section>
  );
}
