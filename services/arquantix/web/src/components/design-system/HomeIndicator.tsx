export function HomeIndicator() {
  return (
    <div className="h-[21px] relative w-full">
      <div className="-translate-x-1/2 absolute bottom-[8px] flex h-[5px] items-center justify-center left-1/2 w-[139px]">
        <div className="-scale-y-100 flex-none rotate-180">
          <div className="bg-white h-[5px] rounded-[100px] w-[139px]" />
        </div>
      </div>
    </div>
  );
}
