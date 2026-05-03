import React from 'react';

interface TestimonialProps {
  authorName: string;
  authorTitle: string;
  authorImage: string;
  rating: number;
  testimonialText: string;
}

function StarRating({ rating }: { rating: number }) {
  const svgPaths = {
    star: "M12 2L14.472 9.26604L22 9.26604L15.764 13.968L18.236 21.234L12 16.532L5.764 21.234L8.236 13.968L2 9.26604L9.528 9.26604L12 2Z"
  };

  return (
    <div className="h-[24px] relative shrink-0 w-[128px]">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 128 24">
        <g>
          {[0, 1, 2, 3, 4].map((index) => (
            <path
              key={index}
              d={svgPaths.star}
              fill={index < rating ? `url(#gradient-${index})` : "#E0E0E0"}
              transform={`translate(${index * 26}, 0)`}
            />
          ))}
        </g>
        <defs>
          {[0, 1, 2, 3, 4].map((index) => (
            <linearGradient
              key={index}
              gradientUnits="userSpaceOnUse"
              id={`gradient-${index}`}
              x1={12 + index * 26}
              x2={12 + index * 26}
              y1="0"
              y2="24"
            >
              <stop stopColor="#E885D0" />
              <stop offset="1" stopColor="#FFB84D" />
            </linearGradient>
          ))}
        </defs>
      </svg>
    </div>
  );
}

export function Testimonial({
  authorName,
  authorTitle,
  authorImage,
  rating,
  testimonialText,
}: TestimonialProps) {
  return (
    <div className="bg-[#f3f3f3] flex-[1_0_0] min-h-px min-w-px relative rounded-[10px]">
      <div className="content-stretch flex flex-col gap-[24px] items-start p-[24px] relative w-full">
        {/* Author Section */}
        <div className="content-stretch flex gap-[16px] items-center relative shrink-0 w-full">
          <div
            aria-hidden="true"
            className="relative rounded-[8px] shrink-0 size-[48px]"
            role="presentation"
          >
            <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-[8px]">
              <img
                alt={`Photo de ${authorName}`}
                className="absolute h-full w-full object-cover"
                src={authorImage}
              />
            </div>
          </div>

          <div className="content-stretch flex flex-[1_0_0] flex-col gap-[2px] items-start min-h-px min-w-px not-italic relative">
            <div className="flex flex-col font-['Avenir:Heavy',sans-serif] justify-center leading-[0] relative shrink-0 text-[18px] text-black tracking-[-0.18px] w-full">
              <p className="leading-[1.6]">{authorName}</p>
            </div>
            <p className="font-['Avenir:Book',sans-serif] leading-[1.6] relative shrink-0 text-[#62656e] text-[14px] w-full">
              {authorTitle}
            </p>
          </div>
        </div>

        {/* Divider */}
        <div className="h-0 relative shrink-0 w-full">
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 330.667 1">
              <line opacity="0.3" stroke="#62656E" strokeLinecap="round" x1="0.5" x2="330.167" y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>

        {/* Testimonial Content */}
        <div className="content-stretch flex flex-col gap-[16px] items-start relative shrink-0 w-full">
          <StarRating rating={rating} />
          <p className="font-['Avenir:Book',sans-serif] leading-[1.6] min-w-full not-italic relative shrink-0 text-[14px] text-black w-[min-content]">
            {testimonialText}
          </p>
        </div>
      </div>
    </div>
  );
}
