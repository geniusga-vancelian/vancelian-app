import svgPaths from "../../../imports/svg-y785mg5egn";

interface LogoProps {
  variant?: 'primary' | 'secondary';
  size?: 'small' | 'medium' | 'large';
}

export function Logo({ variant = 'primary', size = 'large' }: LogoProps) {
  const dimensions = {
    small: { width: 188, height: 25 },
    medium: { width: 288, height: 38 },
    large: { width: 432, height: 58 }
  };
  
  const colors = {
    primary: '#1E1C1B',
    secondary: '#8A8A8A'
  };

  const { width, height } = dimensions[size];
  const fill = colors[variant];

  if (size === 'small' || size === 'medium') {
    return (
      <div className="overflow-clip relative shrink-0" style={{ height, width }} data-name="Logo">
        <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox={`0 0 ${size === 'small' ? '188 25' : '288 38'}`}>
          <g clipPath={`url(#clip0_logo_${size})`} id="Calque_1">
            <path d={svgPaths.p1d2661c0} fill={fill} id="Vector" />
            <g id="Group">
              <path d={svgPaths.p233d7000} fill={fill} id="Vector_2" />
              <path d={svgPaths.p3eb2d100} fill={fill} id="Vector_3" />
              <path d={svgPaths.p350a400} fill={fill} id="Vector_4" />
              <path d={svgPaths.p15759680} fill={fill} id="Vector_5" />
              <path d={svgPaths.p233da780} fill={fill} id="Vector_6" />
              <path d={svgPaths.p19e73200} fill={fill} id="Vector_7" />
              <path d={svgPaths.p39c095f0} fill={fill} id="Vector_8" />
              <path d={svgPaths.p14f9a080} fill={fill} id="Vector_9" />
              <path d={svgPaths.pa33c780} fill={fill} id="Vector_10" />
            </g>
          </g>
          <defs>
            <clipPath id={`clip0_logo_${size}`}>
              <rect fill="white" height={height} width={width} />
            </clipPath>
          </defs>
        </svg>
      </div>
    );
  }

  return (
    <div className="overflow-clip relative shrink-0" style={{ height, width }} data-name="Logo">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 432 58">
        <g clipPath="url(#clip0_logo_large)" id="Calque_1">
          <path d={svgPaths.p2b851980} fill={fill} id="Vector" />
          <g id="Group">
            <path d={svgPaths.p1c1ef580} fill={fill} id="Vector_2" />
            <path d={svgPaths.p1416a000} fill={fill} id="Vector_3" />
            <path d={svgPaths.p314cc100} fill={fill} id="Vector_4" />
            <path d={svgPaths.p28d0600} fill={fill} id="Vector_5" />
            <path d={svgPaths.p1abff300} fill={fill} id="Vector_6" />
            <path d={svgPaths.p23c29040} fill={fill} id="Vector_7" />
            <path d={svgPaths.p2cf50580} fill={fill} id="Vector_8" />
            <path d={svgPaths.p1fe8f880} fill={fill} id="Vector_9" />
            <path d={svgPaths.p1e02980} fill={fill} id="Vector_10" />
          </g>
        </g>
        <defs>
          <clipPath id="clip0_logo_large">
            <rect fill="white" height="58" width="432" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}
