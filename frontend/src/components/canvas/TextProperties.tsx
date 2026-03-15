import React, { useState, useEffect, useCallback } from 'react';
import type { FabricObject, Canvas, Textbox } from 'fabric';
import ColorPicker from './ColorPicker';
import FontPicker from './FontPicker';

interface TextPropertiesProps {
  object: FabricObject;
  canvas: Canvas;
  onModified: () => void;
}

const TextProperties: React.FC<TextPropertiesProps> = ({ object, canvas, onModified }) => {
  const textObj = object as Textbox;

  const [fontFamily, setFontFamily] = useState('');
  const [fontSize, setFontSize] = useState(20);
  const [fill, setFill] = useState('#ffffff');
  const [bold, setBold] = useState(false);
  const [italic, setItalic] = useState(false);
  const [underline, setUnderline] = useState(false);
  const [textAlign, setTextAlign] = useState('left');

  const syncFromObject = useCallback(() => {
    setFontFamily(textObj.fontFamily ?? 'Arial');
    setFontSize(textObj.fontSize ?? 20);
    setFill((textObj.fill as string) ?? '#ffffff');
    setBold(textObj.fontWeight === 'bold');
    setItalic(textObj.fontStyle === 'italic');
    setUnderline(textObj.underline ?? false);
    setTextAlign(textObj.textAlign ?? 'left');
  }, [textObj]);

  useEffect(() => {
    syncFromObject();
  }, [syncFromObject]);

  const apply = (props: Record<string, any>) => {
    textObj.set(props);
    canvas.requestRenderAll();
    onModified();
  };

  return (
    <div className="space-y-3">
      <h3 className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Text</h3>

      <FontPicker
        value={fontFamily}
        onChange={(v) => { setFontFamily(v); apply({ fontFamily: v }); }}
      />

      <div className="flex items-center gap-2">
        <div className="flex-1">
          <label className="block text-[10px] text-gray-500 mb-0.5">Size</label>
          <input
            type="number"
            value={fontSize}
            min={1}
            max={999}
            onChange={(e) => { const v = parseInt(e.target.value) || 20; setFontSize(v); apply({ fontSize: v }); }}
            className="w-full px-2 py-1 bg-dark-700 border border-dark-600 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
      </div>

      <ColorPicker label="Color" color={fill} onChange={(v) => { setFill(v); apply({ fill: v }); }} />

      <div>
        <label className="block text-[10px] text-gray-500 mb-1">Style</label>
        <div className="flex gap-1">
          <button
            onClick={() => { const v = !bold; setBold(v); apply({ fontWeight: v ? 'bold' : 'normal' }); }}
            className={`px-2.5 py-1 rounded text-xs font-bold transition-colors ${bold ? 'bg-primary-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'}`}
          >
            B
          </button>
          <button
            onClick={() => { const v = !italic; setItalic(v); apply({ fontStyle: v ? 'italic' : 'normal' }); }}
            className={`px-2.5 py-1 rounded text-xs italic transition-colors ${italic ? 'bg-primary-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'}`}
          >
            I
          </button>
          <button
            onClick={() => { const v = !underline; setUnderline(v); apply({ underline: v }); }}
            className={`px-2.5 py-1 rounded text-xs underline transition-colors ${underline ? 'bg-primary-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'}`}
          >
            U
          </button>
        </div>
      </div>

      <div>
        <label className="block text-[10px] text-gray-500 mb-1">Alignment</label>
        <div className="flex gap-1">
          {(['left', 'center', 'right'] as const).map((a) => (
            <button
              key={a}
              onClick={() => { setTextAlign(a); apply({ textAlign: a }); }}
              className={`flex-1 px-2 py-1 rounded text-xs capitalize transition-colors ${textAlign === a ? 'bg-primary-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'}`}
            >
              {a}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TextProperties;
