interface TextInputProps {
     type?: string;
     placeholder?: string;
     value?: string;
     onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
     className?: string;
     required?: boolean;
     minLength?: number;
}

export default function TextInput({
     type = "text",
     placeholder = "",
     value,
     onChange,
     className = "",
     required = false,
     minLength,
}: TextInputProps) {
     return (
          <input
               type={type}
               placeholder={placeholder}
               value={value}
               onChange={onChange}
               required={required}
               minLength={minLength}
               className={`text-base font-normal leading-[120%] text-white placeholder:text-white/[60%] w-full px-4 bg-black-1100 border border-blue-1100 h-12 rounded-lg ${className}`}
          />
     );
}
