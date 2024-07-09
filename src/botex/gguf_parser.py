import struct

class GGUFParser:
    def __init__(self, gguf_file_path):
        self.gguf_file_path = gguf_file_path
    

    def get_metadata(self):
        meta_data = {}
        with open(self.gguf_file_path, 'rb') as f:
            magic_number = f.read(4)
            if magic_number != b"GGUF":
                raise ValueError("Invalid GGUF file")

            version = struct.unpack("I", f.read(4))[0]
            if version != 3:
                raise ValueError("Unsupported GGUF version")

            _ = struct.unpack("Q", f.read(8))[0]
            metadata_kv_count = struct.unpack("Q", f.read(8))[0]

            for _ in range(metadata_kv_count):
                key = GGUFParser.read_string(f)
                value_type = struct.unpack("I", f.read(4))[0]
                value = GGUFParser.read_value(f, value_type)

                if 'context_length' in key:
                    meta_data['context_length'] = value
                
        
        return meta_data

    @staticmethod
    def read_string(file):
        length = struct.unpack("Q", file.read(8))[0]
        return file.read(length).decode('utf-8')
    
    @staticmethod
    def read_array(file, element_type):
        length = struct.unpack("Q", file.read(8))[0]
        if element_type == "str":
            return [GGUFParser.read_string(file) for _ in range(length)]
        elif element_type == "f32":
            return struct.unpack(f"{length}f", file.read(length * 4))
        elif element_type == "i32":
            return struct.unpack(f"{length}i", file.read(length * 4))
        else:
            raise ValueError(f"Unsupported array element type: {element_type}")
        
    @staticmethod
    def read_value(file, value_type):
        VALUE_FORMATS = {
            0: "B",  # UINT8
            1: "b",  # INT8
            2: "H",  # UINT16
            3: "h",  # INT16
            4: "I",  # UINT32
            5: "i",  # INT32
            6: "f",  # FLOAT32
            7: "?",  # BOOL
            10: "Q", # UINT64
            11: "q", # INT64
            12: "d", # FLOAT64
            8: GGUFParser.read_string,  # STRING
            9: GGUFParser.read_array,   # ARRAY
        }
        if value_type in VALUE_FORMATS:
            if callable(VALUE_FORMATS[value_type]):
                if value_type == 9:
                    array_type = struct.unpack("I", file.read(4))[0]
                    if array_type == 8:
                        return GGUFParser.read_array(file, "str")
                    elif array_type == 6:
                        return GGUFParser.read_array(file, "f32")
                    elif array_type == 5:
                        return GGUFParser.read_array(file, "i32")
                    else:
                        raise ValueError(f"Unsupported array type: {array_type}")
                return VALUE_FORMATS[value_type](file)
            return struct.unpack(VALUE_FORMATS[value_type], file.read(struct.calcsize(VALUE_FORMATS[value_type])))[0]
        else:
            raise ValueError("Unsupported value type")