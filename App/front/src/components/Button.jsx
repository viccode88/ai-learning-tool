import React from "react";
import PropTypes from "prop-types";

function Button({ label, onClick, color}) {
    return <
        button onClick={onClick}
        className="px-4 py-2 bg-blue-500 text-white rounded hover:{color}"
    >{label}</button>;
}

Button.propTypes = {
    label: PropTypes.string.isRequired,  // label 必须是字符串且必填
    onClick: PropTypes.func,             // onClick 是函数（可选）
    color: PropTypes.string              // color 是字符串（可选）
};

export default Button;
